"""
Scrapy pipelines — ordered by priority:

  1. DedupePipeline          (100) — drops items whose link is already in the sheet
  2. LinkValidationPipeline  (150) — drops items whose application_link is dead (404/DNS)
  3. SheetsPipeline          (200) — writes to Nigeria or International tab

  GeminiPipeline is implemented in gemini_scoring.py and commented out
  in ITEM_PIPELINES (settings.py). See that file for the full rationale.
  To reactivate: uncomment GeminiPipeline in settings.py and add GEMINI_API_KEY secret.

Sheet columns (5 total):
  Title | Category | Application Link | Deadline | Date Added
"""

import logging
import os
import ssl
import urllib.error
import urllib.request
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
    "Application Link",  # C  <- direct org apply URL
    "Deadline",          # D
    "Date Added",        # E
]
LINK_COL_INDEX = 2

TAB_NIGERIA       = "Nigeria"
TAB_INTERNATIONAL = "International"

# HTTP codes that mean "bot blocked but page is real" — students can open these fine
_BOT_BLOCK_CODES = {403, 405, 406, 429, 503}

# Browser-style User-Agent used for all link checks
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def _is_link_alive(url: str, timeout: int = 7) -> bool:
    """
    Return True when a student can plausibly open *url* in a browser.

    Rules:
    - 2xx / 3xx (after redirect)  → alive
    - 403 / 405 / 429 / 503       → alive  (bot-block; students aren't bots)
    - 404 / 410 / 400              → dead
    - DNS failure / conn refused   → dead
    - Timeout                      → alive  (slow server, not a dead URL)
    - SSL cert error               → ignored (some .gov.ng certs are broken,
                                     but the page is real for students)

    Always tries HEAD first (cheap), falls back to GET on 405/501.
    """
    if not url or not url.startswith("http"):
        return False

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE

    headers = {"User-Agent": _UA}
    last_code = None

    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout, context=ctx):
                return True                          # 2xx/3xx — alive
        except urllib.error.HTTPError as exc:
            last_code = exc.code
            if exc.code in _BOT_BLOCK_CODES:
                return True                          # bot-block — allow
            if method == "HEAD" and exc.code in (405, 501):
                continue                             # server doesn't allow HEAD → retry GET
            return False                             # 404, 410, etc. — dead
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if "timed out" in reason or "time out" in reason.lower():
                return True                          # slow server — allow
            if method == "HEAD":
                continue                             # retry GET before giving up
            return False                             # DNS / connection refused — dead
        except Exception:
            if method == "HEAD":
                continue
            return False

    # Both methods exhausted — trust last HTTP code if we got one
    return last_code in _BOT_BLOCK_CODES if last_code else False


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


class LinkValidationPipeline:
    """
    Validates every new application_link before it reaches SheetsPipeline.

    Runs at priority 150 — after DedupePipeline (100) so it only checks
    genuinely new links, never re-checking URLs already in the sheet.

    Alive:  2xx/3xx, 403/405/429/503 (bot-blocks), timeout (slow server)
    Dead:   404, 410, DNS failure, connection refused → DropItem
    """

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_item(self, item, spider=None):
        link = (item.get("application_link") or "").strip()
        if not link:
            raise DropItem("Empty application_link")

        alive = _is_link_alive(link)
        if alive:
            logger.info("LinkValidation: OK    — %s", link)
        else:
            logger.warning("LinkValidation: DEAD  — dropping %s", link)
            raise DropItem(f"Dead link (404/DNS): {link}")

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
                logger.info("SheetsPipeline: %d rows -> Nigeria tab.", nigeria_written)
            except Exception as exc:
                logger.error("SheetsPipeline: Nigeria write error — %s", exc)

        if self.intl_rows and self.international_ws:
            try:
                self.international_ws.append_rows(self.intl_rows, value_input_option="USER_ENTERED")
                intl_written = len(self.intl_rows)
                logger.info("SheetsPipeline: %d rows -> International tab.", intl_written)
            except Exception as exc:
                logger.error("SheetsPipeline: International write error — %s", exc)

        logger.info(
            "SheetsPipeline SUMMARY: nigeria_new=%d, intl_new=%d, "
            "nigeria_written=%d, intl_written=%d.",
            len(self.nigeria_rows), len(self.intl_rows),
            nigeria_written, intl_written,
        )
