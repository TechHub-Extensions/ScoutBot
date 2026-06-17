"""
Scrapy pipelines:
  1. DedupePipeline        — drops duplicates (same link seen in this run)
  2. SheetsPipeline        — writes to separate tabs:
       "Nigeria"       ← range == "National"
       "International" ← range == "International"
     Skips links already present in either tab.
     Adds "Date Added" column (today's date) to every new row.
  3. WhatsAppQueuePipeline — closes the broadcast gap: writes every newly-scraped
     opportunity to distribution-bridge/opportunities.json AND
     distribution-bridge/whatsapp_queue.db so broadcast.py / any daemon can
     pick them up without a manual import step.
"""

import json
import os
import sqlite3
import logging
from datetime import date
from dotenv import load_dotenv
from scrapy.exceptions import DropItem

load_dotenv()

logger = logging.getLogger(__name__)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

SHEET_HEADERS = [
    "Title",
    "Industry",
    "Category",
    "Range",
    "Education Level",
    "Organization",
    "Summary",
    "Application Link",
    "Opening Date",
    "Deadline",
    "Status",
    "Date Added",
]

LINK_COL_INDEX = 7   # 0-based index of "Application Link"
TAB_NIGERIA       = "Nigeria"
TAB_INTERNATIONAL = "International"

# distribution-bridge/ lives one level above the scoutbot package dir
DISTRIB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "distribution-bridge",
)


def _resolve_json_path():
    p = SERVICE_ACCOUNT_JSON
    if not os.path.isabs(p):
        p = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            p,
        )
    return p


def _get_or_create_tab(spreadsheet, name):
    """Return the named worksheet, creating it with headers if it doesn't exist."""
    try:
        ws = spreadsheet.worksheet(name)
    except Exception:
        ws = spreadsheet.add_worksheet(title=name, rows=2000, cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
        logger.info(f"SheetsPipeline: Created new tab '{name}'.")
    return ws


class DedupePipeline:
    """Drops items whose link has already been seen in this run."""

    def __init__(self):
        self.seen = set()

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider=None):
        link = (item.get("application_link") or "").strip()
        if not link or link in self.seen:
            raise DropItem(f"Duplicate/empty link: {link}")
        self.seen.add(link)
        return item


class SheetsPipeline:
    """Routes opportunities to the Nigeria or International tab."""

    def __init__(self):
        self.nigeria_ws       = None
        self.international_ws = None
        self.existing_links   = set()
        self.nigeria_rows     = []
        self.intl_rows        = []

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider=None):
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            creds = Credentials.from_service_account_file(
                _resolve_json_path(),
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
            client = gspread.authorize(creds)
            ss = client.open_by_key(SPREADSHEET_ID)

            self.nigeria_ws       = _get_or_create_tab(ss, TAB_NIGERIA)
            self.international_ws = _get_or_create_tab(ss, TAB_INTERNATIONAL)

            # Load existing links from BOTH tabs to prevent cross-tab duplicates
            for ws in (self.nigeria_ws, self.international_ws):
                rows = ws.get_all_values()
                for row in rows[1:]:
                    if len(row) > LINK_COL_INDEX and row[LINK_COL_INDEX].strip():
                        self.existing_links.add(row[LINK_COL_INDEX].strip())

            logger.info(
                f"SheetsPipeline: {len(self.existing_links)} existing entries "
                f"loaded from Nigeria + International tabs."
            )
        except Exception as exc:
            logger.error(f"SheetsPipeline: Failed to connect — {exc}")

    def process_item(self, item, spider=None):
        link = (item.get("application_link") or "").strip()
        if link in self.existing_links:
            raise DropItem(f"Already in sheet: {link}")

        today = date.today().isoformat()
        row = [
            (item.get("title") or "").strip(),
            (item.get("industry") or "General").strip(),
            (item.get("category") or "Opportunity").strip(),
            (item.get("range") or "").strip(),
            (item.get("education_level") or "Any").strip(),
            (item.get("organization") or "").strip(),
            (item.get("summary") or "")[:400].strip(),
            link,
            (item.get("opening_date") or "").strip(),
            (item.get("deadline") or "").strip(),
            (item.get("status") or "Open").strip(),
            today,
        ]

        opp_range = (item.get("range") or "").strip()
        if opp_range == "International":
            self.intl_rows.append(row)
        else:
            self.nigeria_rows.append(row)

        self.existing_links.add(link)
        return item

    def close_spider(self, spider=None):
        if self.nigeria_rows and self.nigeria_ws:
            try:
                self.nigeria_ws.append_rows(self.nigeria_rows, value_input_option="USER_ENTERED")
                logger.info(f"SheetsPipeline: {len(self.nigeria_rows)} rows → Nigeria tab.")
            except Exception as exc:
                logger.error(f"SheetsPipeline: Nigeria write error — {exc}")

        if self.intl_rows and self.international_ws:
            try:
                self.international_ws.append_rows(self.intl_rows, value_input_option="USER_ENTERED")
                logger.info(f"SheetsPipeline: {len(self.intl_rows)} rows → International tab.")
            except Exception as exc:
                logger.error(f"SheetsPipeline: International write error — {exc}")

        if not self.nigeria_rows and not self.intl_rows:
            logger.info("SheetsPipeline: No new rows to write.")


class WhatsAppQueuePipeline:
    """
    Closes the pipeline gap (issue #62).

    Collects every item that survived DedupePipeline + SheetsPipeline, then on
    close_spider writes two files inside distribution-bridge/:

      • opportunities.json   — broadcast.py reads this (--source json default)
      • whatsapp_queue.db    — pending_broadcasts table for any polling daemon

    Both files are created fresh each run so broadcast.py always gets exactly
    the new items from this scrape — no stale data accumulation.
    """

    def __init__(self):
        self.new_items = []

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider=None):
        self.new_items.append({
            "title":            (item.get("title") or "").strip(),
            "category":         (item.get("category") or "Opportunity").strip(),
            "industry":         (item.get("industry") or "General").strip(),
            "organization":     (item.get("organization") or "").strip(),
            "summary":          (item.get("summary") or "")[:400].strip(),
            "application_link": (item.get("application_link") or "").strip(),
            "deadline":         (item.get("deadline") or "").strip(),
            "education_level":  (item.get("education_level") or "Any").strip(),
            "range":            (item.get("range") or "").strip(),
            "status":           (item.get("status") or "Open").strip(),
        })
        return item

    def close_spider(self, spider=None):
        if not self.new_items:
            logger.info("WhatsAppQueuePipeline: No new items — nothing to queue.")
            return

        os.makedirs(DISTRIB_DIR, exist_ok=True)

        # ── 1. opportunities.json (broadcast.py --source json) ──────────────
        json_path = os.path.join(DISTRIB_DIR, "opportunities.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.new_items, f, ensure_ascii=False, indent=2)
            logger.info(
                f"WhatsAppQueuePipeline: {len(self.new_items)} items → {json_path}"
            )
        except Exception as exc:
            logger.error(f"WhatsAppQueuePipeline: JSON write error — {exc}")

        # ── 2. whatsapp_queue.db (pending_broadcasts table) ─────────────────
        db_path = os.path.join(DISTRIB_DIR, "whatsapp_queue.db")
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_broadcasts (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    title    TEXT,
                    link     TEXT,
                    deadline TEXT,
                    status   TEXT DEFAULT 'pending'
                )
            """)
            conn.executemany(
                "INSERT INTO pending_broadcasts (title, link, deadline) VALUES (?, ?, ?)",
                [
                    (item["title"], item["application_link"], item["deadline"])
                    for item in self.new_items
                ],
            )
            conn.commit()
            conn.close()
            logger.info(
                f"WhatsAppQueuePipeline: {len(self.new_items)} rows → {db_path}"
            )
        except Exception as exc:
            logger.error(f"WhatsAppQueuePipeline: DB write error — {exc}")
