"""
ScoutBot — Gemini AI Scoring Pipeline

This file contains the GeminiPipeline Scrapy pipeline.
It is the ONLY file in this repository that calls the Gemini API.

What it does:
  1. Receives every scraped opportunity item from DedupePipeline
  2. Sends title + category + summary + deadline to Gemini Flash
  3. Gemini returns: a relevance score (1–10) + a 2-sentence blurb
  4. Items scoring below MIN_SCORE (5) are dropped — never reach the sheet
  5. Items scoring 5+ get their AI Blurb stored in the sheet (column F)

Gemini model:  gemini-flash-latest  (free tier, 15 RPM)
API key:       GEMINI_API_KEY (GitHub Secret → wired into .env by scoutbot.yml)
Rate limiting: 6-second sleep between calls + 3-attempt retry on 429
Free tier:     1,500 requests/day — ScoutBot uses ~5–20/day

Where to find evidence of Gemini running:
  - GitHub Actions logs: search for "GeminiPipeline" in the "Run ScoutBot" step
  - Google Sheet: "AI Blurb" column (column F) in Nigeria / International tabs
  - Email digest: blurb text appears under each opportunity title

Pipeline order in scoutbot/settings.py:
  DedupePipeline (100) → GeminiPipeline (150) → SheetsPipeline (200)
"""

import asyncio
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request

from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/{model}:generateContent"
)

# Use gemini-flash-latest — stable alias always pointing at the current Flash release
GEMINI_MODEL = "gemini-flash-latest"

# Minimum Gemini score to keep an item. Items scoring below this are silently dropped.
MIN_SCORE = 5

# Seconds to sleep between Gemini calls — keeps throughput at ~10 RPM,
# safely within the free-tier 15 RPM limit and leaving headroom for retries.
CALL_INTERVAL = 6.0

# On HTTP 429 (rate limited): retry up to MAX_RETRIES times, waiting RETRY_WAIT
# seconds between attempts.
MAX_RETRIES  = 3
RETRY_WAIT   = 60   # seconds


class GeminiPipeline:
    """Scrapy pipeline — scores each opportunity with Gemini Flash.

    Enabled only when GEMINI_API_KEY is set in the environment.
    If the key is missing or all retries fail, the item passes through with
    an empty blurb so a Gemini outage never silences the daily scrape.

    To enable: add GEMINI_API_KEY to GitHub repo Secrets
    (Settings → Secrets and variables → Actions → New repository secret).
    Get a free key at: https://aistudio.google.com/app/apikey
    """

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider=None):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.enabled = bool(self.api_key)
        self._last_call_time = 0.0   # monotonic time of last Gemini call

        if self.enabled:
            logger.info(
                "GeminiPipeline: AI scoring ENABLED (model: %s, interval: %.0fs, "
                "min_score: %d).",
                GEMINI_MODEL, CALL_INTERVAL, MIN_SCORE,
            )
        else:
            logger.warning(
                "GeminiPipeline: GEMINI_API_KEY not set — AI scoring DISABLED. "
                "Items will pass through with empty blurbs. "
                "Add GEMINI_API_KEY to GitHub Secrets to enable scoring."
            )

    async def process_item(self, item, spider=None):
        if not self.enabled:
            item["ai_blurb"] = ""
            return item
        return await asyncio.to_thread(self._call_gemini, item)

    def _call_gemini(self, item):
        """Rate-limited, retry-aware Gemini call. Runs in a thread pool."""
        # Enforce minimum gap between calls (rate limiting)
        now = time.monotonic()
        gap = now - self._last_call_time
        if gap < CALL_INTERVAL:
            time.sleep(CALL_INTERVAL - gap)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self._call_gemini_inner(item)
                self._last_call_time = time.monotonic()
                return result
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    logger.info(
                        "GeminiPipeline: 429 rate limit on attempt %d/%d — "
                        "waiting %ds then retrying.",
                        attempt, MAX_RETRIES, RETRY_WAIT,
                    )
                    time.sleep(RETRY_WAIT)
                    continue
                # Non-429 HTTP error — log and pass through
                title = (item.get("title") or "")[:60]
                logger.warning(
                    "GeminiPipeline: HTTP %s for \"%s\" — passing through with empty blurb.",
                    exc.code, title,
                )
                item["ai_blurb"] = ""
                self._last_call_time = time.monotonic()
                return item
            except Exception as exc:
                title = (item.get("title") or "")[:60]
                logger.warning(
                    "GeminiPipeline: error for \"%s\" — %s; passing through with empty blurb.",
                    title, exc,
                )
                item["ai_blurb"] = ""
                self._last_call_time = time.monotonic()
                return item

        # All retries exhausted
        title = (item.get("title") or "")[:60]
        logger.warning(
            "GeminiPipeline: all %d retries exhausted for \"%s\" — "
            "passing through with empty blurb.",
            MAX_RETRIES, title,
        )
        item["ai_blurb"] = ""
        self._last_call_time = time.monotonic()
        return item

    def _call_gemini_inner(self, item):
        """Make a single Gemini API call and return the updated item."""
        title    = (item.get("title")    or "").strip()
        category = (item.get("category") or "").strip()
        summary  = (item.get("summary")  or "")[:300].strip()
        deadline = (item.get("deadline") or "").strip()

        prompt = (
            "You help Nigerian university students discover opportunities.\n\n"
            "Rate this opportunity 1–10 for relevance to Nigerian students and write "
            "a punchy 1–2 sentence blurb they can act on immediately.\n"
            "Score 7+ ONLY if it is explicitly open to Nigerians or Africans broadly, "
            "currently accepting applications, and is a genuine scholarship, fellowship, "
            "internship, or training programme.\n\n"
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"Summary: {summary}\n"
            f"Deadline: {deadline}\n\n"
            'Respond in JSON only — no markdown, no code fences:\n'
            '{"score": <1-10>, "blurb": "<1-2 sentence blurb>"}'
        )

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 120},
        }).encode()

        url = f"{GEMINI_URL_TEMPLATE.format(model=GEMINI_MODEL)}?key={self.api_key}"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())

        raw    = resp["candidates"][0]["content"]["parts"][0]["text"]
        raw    = re.sub(r"```[a-z]*\s*|\s*```", "", raw).strip()
        result = json.loads(raw)
        score  = int(result.get("score", 0))
        blurb  = str(result.get("blurb", "")).strip()

        logger.info("GeminiPipeline: score=%d — %s", score, title[:70])

        if score < MIN_SCORE:
            raise DropItem(
                f"GeminiPipeline: score={score} (min {MIN_SCORE}) — \"{title[:60]}\""
            )

        item["ai_blurb"] = blurb
        return item
