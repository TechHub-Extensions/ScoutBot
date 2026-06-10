"""
Scrapy pipelines:
  1. DedupePipeline  — drops duplicates (same link seen in this run)
  2. SheetsPipeline  — writes to separate tabs:
       "Nigeria"       ← range == "National"
       "International" ← range == "International"
     Skips links already present in either tab.
     Adds "Date Added" column (today's date) to every new row.
"""

import os
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
        nigeria_written = 0
        intl_written    = 0

        if self.nigeria_rows and self.nigeria_ws:
            try:
                self.nigeria_ws.append_rows(self.nigeria_rows, value_input_option="USER_ENTERED")
                nigeria_written = len(self.nigeria_rows)
                logger.info(f"SheetsPipeline: {nigeria_written} rows → Nigeria tab.")
            except Exception as exc:
                logger.error(f"SheetsPipeline: Nigeria write error — {exc}")
        elif self.nigeria_rows and not self.nigeria_ws:
            logger.error(
                f"SheetsPipeline: {len(self.nigeria_rows)} Nigeria rows ready "
                "but worksheet handle is None — sheet connection failed in open_spider."
            )

        if self.intl_rows and self.international_ws:
            try:
                self.international_ws.append_rows(self.intl_rows, value_input_option="USER_ENTERED")
                intl_written = len(self.intl_rows)
                logger.info(f"SheetsPipeline: {intl_written} rows → International tab.")
            except Exception as exc:
                logger.error(f"SheetsPipeline: International write error — {exc}")
        elif self.intl_rows and not self.international_ws:
            logger.error(
                f"SheetsPipeline: {len(self.intl_rows)} International rows ready "
                "but worksheet handle is None — sheet connection failed in open_spider."
            )

        logger.info(
            f"SheetsPipeline SUMMARY: "
            f"existing={len(self.existing_links)} loaded, "
            f"nigeria_new={len(self.nigeria_rows)}, intl_new={len(self.intl_rows)}, "
            f"nigeria_written={nigeria_written}, intl_written={intl_written}."
        )
        if not self.nigeria_rows and not self.intl_rows:
            logger.info(
                "SheetsPipeline: No new rows — either all items were duplicates "
                "of the %d existing links, or the spider found nothing new.",
                len(self.existing_links),
            )
