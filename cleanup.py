"""
ScoutBot cleanup module.

Removes stale or expired opportunities from both the Nigeria and
International tabs in Google Sheets.

A row is removed when ANY of the following are true:
  1. Deadline is a parseable date that has already passed
  2. Date Added is older than STALE_DAYS (23) days — hard cap, no exceptions

Uses header-name lookup (not column indices) so it works correctly with
both the new 6-column schema and any future schema changes.

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

STALE_DAYS = 23   # entries older than this are removed unconditionally

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


def _col_index(headers, name):
    """Return the 0-based index of a column header, or -1 if not found."""
    try:
        return [h.strip() for h in headers].index(name)
    except ValueError:
        return -1


def cleanup_worksheet(ws, today):
    """Remove expired / stale rows. Returns count removed.

    Finds 'Deadline' and 'Date Added' columns by header name, not by
    hardcoded index — works with any column order or schema version.
    """
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return 0

    headers           = all_values[0]
    deadline_idx      = _col_index(headers, "Deadline")
    date_added_idx    = _col_index(headers, "Date Added")

    stale_cutoff = today - timedelta(days=STALE_DAYS)
    rows_to_delete = []

    for row_num, row in enumerate(all_values[1:], start=2):
        def cell(idx):
            return row[idx].strip() if idx >= 0 and idx < len(row) else ""

        deadline_text = cell(deadline_idx)
        date_added    = cell(date_added_idx)
        should_delete = False

        # Rule 1: deadline already passed
        if not should_delete and deadline_text:
            deadline_date = parse_deadline(deadline_text)
            if deadline_date and deadline_date < today:
                should_delete = True

        # Rule 2: hard stale cap (STALE_DAYS days after Date Added)
        if not should_delete and date_added:
            try:
                added = date.fromisoformat(date_added)
                if added < stale_cutoff:
                    should_delete = True
            except Exception:
                pass

        if should_delete:
            rows_to_delete.append(row_num)

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
                logger.info("cleanup: Tab '%s' not found — skipping.", tab_name)
                continue
            removed = cleanup_worksheet(ws, today)
            logger.info("cleanup: Removed %d rows from '%s' tab.", removed, tab_name)
            total += removed

        logger.info("cleanup: Total %d rows removed across all tabs.", total)
        return total

    except Exception as exc:
        logger.error("cleanup: Failed — %s", exc)
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cleanup()
