"""
ScoutBot cleanup module.

Removes closed opportunities from the Google Sheet so the spreadsheet only
contains live, actionable opportunities.

A row is considered closed (and removed) when:
  1. Its Status column is explicitly "Closed", OR
  2. Its Deadline column is a parseable date that has already passed.

Rows with "Ongoing", "Rolling", "TBD", or unparseable deadlines are kept.

Run on its own with:  python cleanup.py
Or as part of the pipeline (called from run.py before the email is sent).
"""

import os
import logging
from datetime import date

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

DEADLINE_COL_INDEX = 9   # 0-based column index for "Deadline"
STATUS_COL_INDEX = 10    # 0-based column index for "Status"

NON_DATE_MARKERS = {
    "ongoing", "rolling", "open", "tbd", "tba",
    "varies", "various", "n/a", "na", "", "-",
}


def parse_deadline(text):
    """
    Try to extract a date from free-text deadline text.
    Returns a `date` object on success, or None if unparseable / non-date.
    """
    if not text:
        return None
    text = text.strip()
    if text.lower() in NON_DATE_MARKERS:
        return None

    try:
        from dateutil.parser import parse as dateutil_parse
        dt = dateutil_parse(text, fuzzy=True, dayfirst=False)
        return dt.date()
    except Exception:
        return None


def cleanup():
    """
    Connect to Google Sheets and delete closed opportunities.
    Safe to call repeatedly. Logs how many rows were removed.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        json_path = SERVICE_ACCOUNT_JSON
        if not os.path.isabs(json_path):
            json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), json_path)

        creds = Credentials.from_service_account_file(json_path, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1

        all_values = sheet.get_all_values()
        if len(all_values) <= 1:
            logger.info("cleanup: Sheet is empty or has only the header — nothing to clean.")
            return 0

        today = date.today()
        rows_to_delete = []  # 1-based indexes (matches gspread API)

        # Row 1 = header, so iterate from row 2 onwards
        for sheet_row_index, row in enumerate(all_values[1:], start=2):
            status_text = ""
            deadline_text = ""

            if len(row) > STATUS_COL_INDEX:
                status_text = row[STATUS_COL_INDEX].strip().lower()
            if len(row) > DEADLINE_COL_INDEX:
                deadline_text = row[DEADLINE_COL_INDEX].strip()

            should_delete = False

            if status_text == "closed":
                should_delete = True
            else:
                deadline_date = parse_deadline(deadline_text)
                if deadline_date and deadline_date < today:
                    should_delete = True

            if should_delete:
                rows_to_delete.append(sheet_row_index)

        if not rows_to_delete:
            logger.info("cleanup: No closed opportunities found.")
            return 0

        # Delete from bottom up so row numbers don't shift as we go
        for row_idx in reversed(rows_to_delete):
            sheet.delete_rows(row_idx)

        logger.info(
            f"cleanup: Removed {len(rows_to_delete)} closed opportunities from the sheet."
        )
        return len(rows_to_delete)

    except Exception as exc:
        logger.error(f"cleanup: Failed — {exc}")
        return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    cleanup()
