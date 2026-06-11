"""
ScoutBot — Gemini AI Scoring Pipeline

The ONLY file in this repository that calls the Gemini API.

Pipeline order: DedupePipeline (100) → GeminiPipeline (150) → SheetsPipeline (200)

What it does:
  1. Receives every item that survived DedupePipeline
  2. Sends title + category + summary to Gemini Flash
  3. Gemini returns a relevance score (1–10) + a 2-sentence blurb
  4. Items scoring below MIN_SCORE (5) are dropped permanently
  5. Items scoring 5+ get their AI Blurb written to column F of the sheet

Rate limiting:  6-second gap between calls (~10 RPM, free-tier limit is 15 RPM)
Retry on 429:   up to 3 attempts, 60-second wait between retries
JSON parsing:   robust — strips markdown fences, finds first {...} block in response
Token budget:   256 output tokens (enough for a 2-sentence blurb without truncation)
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

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.0-flash:generateContent"
)

MIN_SCORE     = 5
CALL_INTERVAL = 6.0   # seconds between calls → ~10 RPM (free tier limit: 15 RPM)
MAX_RETRIES   = 3
RETRY_WAIT    = 60    # seconds to wait on HTTP 429


class GeminiPipeline:
    """Score each opportunity with Gemini Flash; drop score < MIN_SCORE."""

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def open_spider(self, spider=None):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.enabled = bool(self.api_key)
        self._last_call = 0.0

        if self.enabled:
            logger.info(
                "GeminiPipeline: ENABLED — model=gemini-2.0-flash, "
                "interval=%.0fs, min_score=%d",
                CALL_INTERVAL, MIN_SCORE,
            )
        else:
            logger.warning(
                "GeminiPipeline: GEMINI_API_KEY not set — AI scoring DISABLED. "
                "All items will pass through with empty blurbs."
            )

    async def process_item(self, item, spider=None):
        if not self.enabled:
            item["ai_blurb"] = ""
            return item
        return await asyncio.to_thread(self._score, item)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _score(self, item):
        """Rate-limited, retry-aware Gemini call. Runs in a thread pool."""
        # Enforce minimum gap between calls
        gap = time.monotonic() - self._last_call
        if gap < CALL_INTERVAL:
            time.sleep(CALL_INTERVAL - gap)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self._call(item)
                self._last_call = time.monotonic()
                return result
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    logger.info(
                        "GeminiPipeline: 429 on attempt %d/%d for \"%s\" — "
                        "waiting %ds.",
                        attempt, MAX_RETRIES,
                        (item.get("title") or "")[:50], RETRY_WAIT,
                    )
                    time.sleep(RETRY_WAIT)
                    continue
                logger.warning(
                    "GeminiPipeline: HTTP %s for \"%s\" — empty blurb.",
                    exc.code, (item.get("title") or "")[:50],
                )
                item["ai_blurb"] = ""
                self._last_call = time.monotonic()
                return item
            except Exception as exc:
                logger.warning(
                    "GeminiPipeline: error for \"%s\" — %s — empty blurb.",
                    (item.get("title") or "")[:50], exc,
                )
                item["ai_blurb"] = ""
                self._last_call = time.monotonic()
                return item

        logger.warning(
            "GeminiPipeline: all retries exhausted for \"%s\" — empty blurb.",
            (item.get("title") or "")[:50],
        )
        item["ai_blurb"] = ""
        self._last_call = time.monotonic()
        return item

    def _call(self, item):
        """Single Gemini API call. Returns updated item or raises."""
        title    = (item.get("title")    or "").strip()
        category = (item.get("category") or "").strip()
        summary  = (item.get("summary")  or "")[:300].strip()
        deadline = (item.get("deadline") or "").strip()

        prompt = (
            "You help Nigerian university students find opportunities.\n\n"
            "Rate this opportunity 1–10 for relevance to Nigerian students "
            "and write a punchy 1–2 sentence blurb they can act on immediately.\n"
            "Score 7+ ONLY if it is explicitly open to Nigerians or Africans broadly, "
            "currently accepting applications, and is a genuine scholarship, fellowship, "
            "or internship.\n\n"
            f"Title: {title}\n"
            f"Category: {category}\n"
            f"Summary: {summary}\n"
            f"Deadline: {deadline}\n\n"
            "Respond with ONLY a JSON object — no markdown, no explanation:\n"
            '{"score": <integer 1-10>, "blurb": "<1-2 sentences>"}'
        )

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 256,   # was 120 — enough for 2-sentence blurb
            },
        }).encode()

        req = urllib.request.Request(
            f"{GEMINI_URL}?key={self.api_key}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())

        raw = resp["candidates"][0]["content"]["parts"][0]["text"]

        # Robust JSON extraction:
        # 1. Strip markdown code fences (```json ... ```)
        raw = re.sub(r"```[a-z]*\s*", "", raw)
        raw = re.sub(r"\s*```", "", raw).strip()
        # 2. Find first { ... } block (handles "Here is the JSON: {...}" responses)
        start = raw.find("{")
        end   = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"No JSON object found in Gemini response: {raw[:100]!r}")
        result = json.loads(raw[start : end + 1])

        score = int(result.get("score", 0))
        blurb = str(result.get("blurb", "")).strip()

        logger.info("GeminiPipeline: score=%d — %.70s", score, title)

        if score < MIN_SCORE:
            raise DropItem(
                f"GeminiPipeline: score={score} < {MIN_SCORE} — \"{title[:60]}\""
            )

        item["ai_blurb"] = blurb
        return item
