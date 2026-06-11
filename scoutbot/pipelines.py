"""
Scrapy pipelines — ordered by priority:

  1. DedupePipeline  (100) — drops items whose link is already in the sheet
  2. GeminiPipeline  (150) — scores with Gemini; drops score < 5; adds AI blurb
                             (imported from scoutbot/gemini_scoring.py)
  3. SheetsPipeline  (200) — writes to Nigeria or International tab

Sheet columns (6 total):
  Title | Category | Application Link | Deadline | Date Added | AI Blurb
"""

import logging
import os
from datetime import date

from dotenv import load_dotenv
from scrapy.exceptions import DropItem

# GeminiPipeline lives in its own file for visibility — import it here
from scoutbot.gemini_scoring import GeminiPipeline  # noqa: F401  (re-exported for settings.py)

load_dotenv()

logger = logging.getLogger(__name__)

SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

# ── Clean 6-column sheet schema ───────────────────────────────────────────────
SHEET_HEADERS = [
    "Title",             # A (col 0)
    "Category",          # B (col 1)
    "Application Link",  # C (col 2)  ← direct apply URL
    "Deadline",          # D (col 3)
    "Date Added",        # E (col 4)
    "AI Blurb",          # F (col 5)  ← Gemini-generated, empty if key not set
]
LINK_COL_INDEX  = 2   # "Application Link" is column C (0-based)

TAB_NIGERIA       = "Nigeria"
TAB_INTERNATIONAL = "International"


def _resolve_json_path():
    p = SERVICE_ACCOUNT_JSON
    if not os.path.isabs(p):
        p = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            p,
        )
    return p


def _get_sheet_client():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(
        _resolve_json_path(),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


def _ensure_tab(spreadsheet, name):
    """Return the worksheet, creating it with correct headers if it does not exist.
    If the tab exists with the old 13-column schema, migrate it: clear data rows
    and set new headers so all future rows use the clean 6-column format.
    Old rows with wrong links are removed as part of this migration.
    """
    try:
        ws = spreadsheet.worksheet(name)
    except Exception:
        ws = spreadsheet.add_worksheet(title=name, rows=2000, cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
        logger.info("SheetsPipeline: Created tab '%s' with new 6-column schema.", name)
        return ws

    # Check if headers already match the new schema
    existing_headers = ws.row_values(1)
    if existing_headers == SHEET_HEADERS:
        return ws   # already migrated

    # Old schema detected — migrate: clear all rows and set new headers
    logger.info(
        "SheetsPipeline: Tab '%s' has old schema (%d cols) — migrating to 6-column schema. "
        "Existing rows cleared (they had wrong application links anyway).",
        name, len(existing_headers),
    )
    ws.clear()
    ws.append_row(SHEET_HEADERS)
    return ws


# ---------------------------------------------------------------------------
# 1. DedupePipeline
# ---------------------------------------------------------------------------

class DedupePipeline:
    """Drops duplicate items before Gemini scoring.

    Pre-loads existing sheet links so items already in the sheet never
    reach GeminiPipeline — avoids burning free-tier Gemini quota on
    items that will be discarded anyway.
    """

    def __init__(self):
        self.seen     = set()   # within-run dedup
        self.existing = set()   # pre-loaded from live sheet

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider=None):
        try:
            client = _get_sheet_client()
            ss     = client.open_by_key(SPREADSHEET_ID)
            for tab_name in (TAB_NIGERIA, TAB_INTERNATIONAL):
                try:
                    ws = ss.worksheet(tab_name)
                    for row in ws.get_all_values()[1:]:
                        if len(row) > LINK_COL_INDEX and row[LINK_COL_INDEX].strip():
                            self.existing.add(row[LINK_COL_INDEX].strip())
                except Exception:
                    pass
            logger.info(
                "DedupePipeline: %d existing links pre-loaded.", len(self.existing),
            )
        except Exception as exc:
            logger.warning("DedupePipeline: Could not pre-load sheet links — %s", exc)

    def process_item(self, item, spider=None):
        link = (item.get("application_link") or "").strip()
        if not link or link in self.seen or link in self.existing:
            raise DropItem(f"Duplicate/empty link: {link!r}")
        self.seen.add(link)
        return item


# ---------------------------------------------------------------------------
# 3. SheetsPipeline  (GeminiPipeline is #2, imported from gemini_scoring.py)
# ---------------------------------------------------------------------------

class SheetsPipeline:
    """Writes opportunities to Nigeria or International tab.

    Uses the clean 6-column schema: Title | Category | Application Link |
    Deadline | Date Added | AI Blurb.

    Migrates old 13-column tabs automatically on first run.
    """

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
            client = _get_sheet_client()
            ss     = client.open_by_key(SPREADSHEET_ID)
            self.nigeria_ws       = _ensure_tab(ss, TAB_NIGERIA)
            self.international_ws = _ensure_tab(ss, TAB_INTERNATIONAL)

            for ws in (self.nigeria_ws, self.international_ws):
                for row in ws.get_all_values()[1:]:
                    if len(row) > LINK_COL_INDEX and row[LINK_COL_INDEX].strip():
                        self.existing_links.add(row[LINK_COL_INDEX].strip())

            logger.info(
                "SheetsPipeline: %d existing entries loaded.", len(self.existing_links),
            )
        except Exception as exc:
            logger.error("SheetsPipeline: Failed to connect — %s", exc)

    def process_item(self, item, spider=None):
        link = (item.get("application_link") or "").strip()
        if link in self.existing_links:
            raise DropItem(f"Already in sheet: {link}")

        today = date.today().isoformat()
        row = [
            (item.get("title")    or "").strip(),           # A: Title
            (item.get("category") or "Opportunity").strip(), # B: Category
            link,                                            # C: Application Link
            (item.get("deadline") or "").strip(),            # D: Deadline
            today,                                           # E: Date Added
            (item.get("ai_blurb") or "").strip(),            # F: AI Blurb
        ]

        if (item.get("range") or "").strip() == "International":
            self.intl_rows.append(row)
        else:
            self.nigeria_rows.append(row)

        self.existing_links.add(link)
        return item

    def close_spider(self, spider=None):
        nigeria_written = 0
        intl_written    = 0

        if self.nigeria_rows and self.nigeria_ws:
            try:
                self.nigeria_ws.append_rows(self.nigeria_rows, value_input_option="USER_ENTERED")
                nigeria_written = len(self.nigeria_rows)
                logger.info("SheetsPipeline: %d rows → Nigeria tab.", nigeria_written)
            except Exception as exc:
                logger.error("SheetsPipeline: Nigeria write error — %s", exc)

        if self.intl_rows and self.international_ws:
            try:
                self.international_ws.append_rows(self.intl_rows, value_input_option="USER_ENTERED")
                intl_written = len(self.intl_rows)
                logger.info("SheetsPipeline: %d rows → International tab.", intl_written)
            except Exception as exc:
                logger.error("SheetsPipeline: International write error — %s", exc)

        logger.info(
            "SheetsPipeline SUMMARY: nigeria_new=%d, intl_new=%d, "
            "nigeria_written=%d, intl_written=%d.",
            len(self.nigeria_rows), len(self.intl_rows),
            nigeria_written, intl_written,
        )
