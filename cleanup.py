"""
ScoutBot cleanup module.

Removes closed or stale opportunities from BOTH the Nigeria and
International tabs in Google Sheets.

A row is removed when ANY of the following are true:
  1. Status column == "Closed"
  2. Deadline is a parseable date that has already passed
  3. Date Added is > STALE_DAYS (23) days ago — hard cap applied to every row
     regardless of deadline, so no entry lingers longer than 23 days

Run standalone:  python cleanup.py
Or called automatically from run.py after every scrape.
"""

import os
import logging
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

DEADLINE_COL_INDEX   = 9   # 0-based
STATUS_COL_INDEX     = 10  # 0-based
DATE_ADDED_COL_INDEX = 11  # 0-based — new column

STALE_DAYS = 23   # hard cap — every entry is removed 23 days after being added

NON_DATE_MARKERS = {
    "ongoing", "rolling", "open", "tbd", "tba",
    "varies", "various", "n/a", "na", "", "-",
}

TAB_NAMES = ["Nigeria", "International"]


def parse_deadline(text):
    if not text:
        return None
    text = text.strip()
    if text.lower() in NON_DATE_MARKERS:
        return None
    try:
        from dateutil.parser import parse as dateutil_parse
        return dateutil_parse(text, fuzzy=True, dayfirst=False).date()
    except Exception:
        return None


def cleanup_worksheet(ws, today):
    """Remove expired / stale rows from a single worksheet. Returns count removed."""
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return 0

    stale_cutoff = today - timedelta(days=STALE_DAYS)
    rows_to_delete = []

    for idx, row in enumerate(all_values[1:], start=2):
        status_text   = row[STATUS_COL_INDEX].strip().lower()   if len(row) > STATUS_COL_INDEX   else ""
        deadline_text = row[DEADLINE_COL_INDEX].strip()         if len(row) > DEADLINE_COL_INDEX  else ""
        date_added    = row[DATE_ADDED_COL_INDEX].strip()       if len(row) > DATE_ADDED_COL_INDEX else ""

        should_delete = False

        # Rule 1: explicitly closed
        if status_text == "closed":
            should_delete = True

        # Rule 2: deadline has already passed
        if not should_delete:
            deadline_date = parse_deadline(deadline_text)
            if deadline_date and deadline_date < today:
                should_delete = True

        # Rule 3: hard 33-day cap — remove regardless of deadline
        if not should_delete and date_added:
            try:
                added = date.fromisoformat(date_added)
                if added < stale_cutoff:
                    should_delete = True
            except Exception:
                pass

        if should_delete:
            rows_to_delete.append(idx)

    for row_idx in reversed(rows_to_delete):
        ws.delete_rows(row_idx)

    return len(rows_to_delete)


def cleanup():
    """Run cleanup on all opportunity tabs. Returns total rows removed."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        json_path = SERVICE_ACCOUNT_JSON
        if not os.path.isabs(json_path):
            json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), json_path)

        creds = Credentials.from_service_account_file(
            json_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        client = gspread.authorize(creds)
        ss     = client.open_by_key(SPREADSHEET_ID)
        today  = date.today()
        total  = 0

        for tab_name in TAB_NAMES:
            try:
                ws = ss.worksheet(tab_name)
            except Exception:
                logger.info(f"cleanup: Tab '{tab_name}' not found — skipping.")
                continue
            removed = cleanup_worksheet(ws, today)
            logger.info(f"cleanup: Removed {removed} rows from '{tab_name}' tab.")
            total += removed

        logger.info(f"cleanup: Total {total} rows removed across all tabs.")
        return total

    except Exception as exc:
        logger.error(f"cleanup: Failed — {exc}")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cleanup()
