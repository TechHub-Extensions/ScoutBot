"""
Scrapy pipelines — ordered by priority:

  1. DedupePipeline  (100) — drops items whose link is already in the sheet
  2. SheetsPipeline  (200) — writes to Nigeria or International tab

Sheet columns (5 total):
  Title | Category | Application Link | Deadline | Date Added
"""

import logging
import os
from datetime import date

from dotenv import load_dotenv
from scrapy.exceptions import DropItem

load_dotenv()

logger = logging.getLogger(__name__)

SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

SHEET_HEADERS = [
    "Title",             # A
    "Category",          # B
    "Application Link",  # C  ← direct org apply URL
    "Deadline",          # D
    "Date Added",        # E
]
LINK_COL_INDEX = 2

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
    try:
        ws = spreadsheet.worksheet(name)
    except Exception:
        ws = spreadsheet.add_worksheet(title=name, rows=2000, cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
        logger.info("SheetsPipeline: Created tab '%s'.", name)
        return ws

    existing = ws.row_values(1)
    if existing[:len(SHEET_HEADERS)] == SHEET_HEADERS:
        return ws

    # Headers mismatch — update header row only (preserve data rows)
    ws.update("A1", [SHEET_HEADERS])
    logger.info("SheetsPipeline: Updated headers on tab '%s'.", name)
    return ws


class DedupePipeline:
    """Drops items whose application_link already exists in the sheet."""

    def __init__(self):
        self.seen     = set()
        self.existing = set()

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
            logger.info("DedupePipeline: %d existing links pre-loaded.", len(self.existing))
        except Exception as exc:
            logger.warning("DedupePipeline: Could not pre-load sheet links — %s", exc)

    def process_item(self, item, spider=None):
        link = (item.get("application_link") or "").strip()
        if not link or link in self.seen or link in self.existing:
            raise DropItem(f"Duplicate/empty link: {link!r}")
        self.seen.add(link)
        return item


class SheetsPipeline:
    """Writes opportunities to Nigeria or International tab."""

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
            logger.info("SheetsPipeline: %d existing entries loaded.", len(self.existing_links))
        except Exception as exc:
            logger.error("SheetsPipeline: Failed to connect — %s", exc)

    def process_item(self, item, spider=None):
        link = (item.get("application_link") or "").strip()
        if link in self.existing_links:
            raise DropItem(f"Already in sheet: {link}")

        today = date.today().isoformat()
        row = [
            (item.get("title")    or "").strip(),
            (item.get("category") or "Opportunity").strip(),
            link,
            (item.get("deadline") or "").strip(),
            today,
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
