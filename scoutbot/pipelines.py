"""
Scrapy pipelines:
  1. DedupePipeline  — drops duplicates (same link seen in this run)
  2. GeminiPipeline  — scores each item with Gemini Flash; drops score < 5;
                       adds ai_blurb field for the email digest
  3. SheetsPipeline  — writes to separate tabs:
       "Nigeria"       <- range == "National"
       "International" <- range == "International"
     Skips links already present in either tab.
     Adds "Date Added" and "AI Blurb" columns to every new row.
"""

import json
import os
import logging
import re
import threading
import time
import urllib.request
from datetime import date
from dotenv import load_dotenv
from scrapy.exceptions import DropItem
from twisted.internet import defer, threads

load_dotenv()

logger = logging.getLogger(__name__)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

SHEET_HEADERS = [
    "Title",            # 0
    "Industry",         # 1
    "Category",         # 2
    "Range",            # 3
    "Education Level",  # 4
    "Organization",     # 5
    "Summary",          # 6
    "Application Link", # 7
    "Opening Date",     # 8
    "Deadline",         # 9  <- cleanup.py DEADLINE_COL_INDEX
    "Status",           # 10 <- cleanup.py STATUS_COL_INDEX
    "Date Added",       # 11 <- cleanup.py DATE_ADDED_COL_INDEX
    "AI Blurb",         # 12
]

LINK_COL_INDEX    = 7
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
    """Return the named worksheet, creating it with headers if it does not exist."""
    try:
        ws = spreadsheet.worksheet(name)
    except Exception:
        ws = spreadsheet.add_worksheet(title=name, rows=2000, cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
        logger.info("SheetsPipeline: Created new tab '%s'.", name)
    return ws


# ---------------------------------------------------------------------------
# 1. DedupePipeline
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 2. GeminiPipeline
# ---------------------------------------------------------------------------

class GeminiPipeline:
    """Score each opportunity with Gemini Flash and add an AI blurb.

    Items scoring below MIN_SCORE are dropped before they reach the sheet.
    If GEMINI_API_KEY is missing or an API call fails the item passes through
    with an empty blurb so a Gemini outage never silences the daily scrape.
    """

    GEMINI_URL = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-2.0-flash:generateContent"
    )
    MIN_SCORE = 5
    # Free tier allows ~10 RPM; semaphore + delay keeps us safely under that
    _sem = threading.Semaphore(1)

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider=None):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.enabled = bool(self.api_key)
        if self.enabled:
            logger.info("GeminiPipeline: AI scoring enabled.")
        else:
            logger.warning("GeminiPipeline: GEMINI_API_KEY not set — AI scoring disabled.")

    @defer.inlineCallbacks
    def process_item(self, item, spider=None):
        if not self.enabled:
            item["ai_blurb"] = ""
            return item
        result = yield threads.deferToThread(self._call_gemini, item)
        return result

    def _call_gemini(self, item):
        """Blocking Gemini REST call — runs inside deferToThread.

        The class-level semaphore + sleep caps throughput at ~10 RPM so
        we stay within the Gemini free-tier quota even when many items
        arrive simultaneously from multiple RSS feeds.
        """
        with self._sem:
            time.sleep(4)          # ~10 RPM safe for free tier
            return self._call_gemini_inner(item)

    def _call_gemini_inner(self, item):
        """Inner rate-unlimited call — always invoked inside _sem."""
        title    = (item.get("title")    or "").strip()
        category = (item.get("category") or "").strip()
        summary  = (item.get("summary")  or "")[:300].strip()
        deadline = (item.get("deadline") or "").strip()
        json_fmt = '{"score": <1-10>, "blurb": "<1-2 sentence blurb>"}'

        prompt = (
            "You help Nigerian university students discover opportunities.\n\n"
            "Rate this opportunity 1-10 for relevance to Nigerian students and write "
            "a punchy 1-2 sentence blurb they can act on immediately.\n"
            "Rate it 7+ ONLY if it is explicitly open to Nigerians or to Africans broadly, "
            "currently accepting applications, and is a genuine scholarship, fellowship, "
            "internship, or training programme.\n\n"
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"Summary: {summary}\n"
            f"Deadline: {deadline}\n\n"
            f"Respond in JSON only — no markdown, no code fences:\n{json_fmt}"
        )

        try:
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 120},
            }).encode()
            req = urllib.request.Request(
                f"{self.GEMINI_URL}?key={self.api_key}",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as r:
                resp = json.loads(r.read())

            raw   = resp["candidates"][0]["content"]["parts"][0]["text"]
            raw   = re.sub(r"```[a-z]*\s*|\s*```", "", raw).strip()
            result = json.loads(raw)
            score  = int(result.get("score", 0))
            blurb  = str(result.get("blurb", "")).strip()

            if score < self.MIN_SCORE:
                raise DropItem(
                    f"GeminiPipeline: score={score} (min {self.MIN_SCORE}) "
                    f"— \"{title[:60]}\""
                )

            item["ai_blurb"] = blurb
            logger.debug("GeminiPipeline: score=%d — %s", score, title[:60])
            return item

        except DropItem:
            raise
        except Exception as exc:
            logger.warning(
                "GeminiPipeline: API error for \"%s\" — %s; passing through.",
                title[:60], exc,
            )
            item["ai_blurb"] = ""
            return item


# ---------------------------------------------------------------------------
# 3. SheetsPipeline
# ---------------------------------------------------------------------------

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

            for ws in (self.nigeria_ws, self.international_ws):
                for row in ws.get_all_values()[1:]:
                    if len(row) > LINK_COL_INDEX and row[LINK_COL_INDEX].strip():
                        self.existing_links.add(row[LINK_COL_INDEX].strip())

            logger.info(
                "SheetsPipeline: %d existing entries loaded from Nigeria + International tabs.",
                len(self.existing_links),
            )
        except Exception as exc:
            logger.error("SheetsPipeline: Failed to connect — %s", exc)

    def process_item(self, item, spider=None):
        link = (item.get("application_link") or "").strip()
        if link in self.existing_links:
            raise DropItem(f"Already in sheet: {link}")

        today = date.today().isoformat()
        row = [
            (item.get("title")            or "").strip(),
            (item.get("industry")         or "General").strip(),
            (item.get("category")         or "Opportunity").strip(),
            (item.get("range")            or "").strip(),
            (item.get("education_level")  or "Any").strip(),
            (item.get("organization")     or "").strip(),
            (item.get("summary")          or "")[:400].strip(),
            link,
            (item.get("opening_date")     or "").strip(),
            (item.get("deadline")         or "").strip(),
            (item.get("status")           or "Open").strip(),
            today,
            (item.get("ai_blurb")         or "").strip(),
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
            "SheetsPipeline SUMMARY: existing=%d loaded, nigeria_new=%d, intl_new=%d, "
            "nigeria_written=%d, intl_written=%d.",
            len(self.existing_links),
            len(self.nigeria_rows), len(self.intl_rows),
            nigeria_written, intl_written,
        )
        if not self.nigeria_rows and not self.intl_rows:
            logger.info(
                "SheetsPipeline: No new rows — all items were duplicates of the "
                "%d existing links, or the spider found nothing new.",
                len(self.existing_links),
            )
