"""
Scrapy pipelines:
  1. DedupePipeline  — drops duplicates (same link seen in this run)
  2. SheetsPipeline  — writes new items to Google Sheets, skips already-present links
"""

import os
import logging
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
]

LINK_COL_INDEX = 7  # 0-based index of "Application Link" in SHEET_HEADERS


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
    """Appends new opportunities to Google Sheets, skipping already-present links."""

    def __init__(self):
        self.sheet = None
        self.existing_links = set()
        self.new_rows = []

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider=None):
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]

            json_path = SERVICE_ACCOUNT_JSON
            if not os.path.isabs(json_path):
                json_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    json_path,
                )

            creds = Credentials.from_service_account_file(json_path, scopes=scopes)
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(SPREADSHEET_ID).sheet1

            all_values = self.sheet.get_all_values()
            if not all_values:
                self.sheet.append_row(SHEET_HEADERS)
                logger.info("SheetsPipeline: Header row added.")
            else:
                for row in all_values[1:]:
                    if len(row) > LINK_COL_INDEX and row[LINK_COL_INDEX].strip():
                        self.existing_links.add(row[LINK_COL_INDEX].strip())

            logger.info(f"SheetsPipeline: {len(self.existing_links)} existing entries loaded.")

        except Exception as exc:
            logger.error(f"SheetsPipeline: Failed to connect to Google Sheets — {exc}")
            self.sheet = None

    def process_item(self, item, spider=None):
        if self.sheet is None:
            return item

        link = (item.get("application_link") or "").strip()
        if link in self.existing_links:
            raise DropItem(f"Already in sheet: {link}")

        row = [
            (item.get("title") or "").strip(),
            (item.get("industry") or "General").strip(),
            (item.get("category") or "Opportunity").strip(),
            (item.get("range") or "").strip(),
            (item.get("education_level") or "Bachelor").strip(),
            (item.get("organization") or "").strip(),
            (item.get("summary") or "")[:400].strip(),
            link,
            (item.get("opening_date") or "").strip(),
            (item.get("deadline") or "").strip(),
            (item.get("status") or "Open").strip(),
        ]
        self.new_rows.append(row)
        self.existing_links.add(link)
        return item

    def close_spider(self, spider=None):
        if not self.new_rows or self.sheet is None:
            logger.info("SheetsPipeline: No new rows to write.")
            return
        try:
            self.sheet.append_rows(self.new_rows, value_input_option="USER_ENTERED")
            logger.info(f"SheetsPipeline: {len(self.new_rows)} new rows added to Google Sheets.")
        except Exception as exc:
            logger.error(f"SheetsPipeline: Write error — {exc}")
