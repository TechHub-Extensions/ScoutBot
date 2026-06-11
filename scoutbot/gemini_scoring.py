"""
ScoutBot — Gemini AI Scoring Pipeline

This file contains the GeminiPipeline Scrapy pipeline.
It is the ONLY file in this repository that calls the Gemini API.

What it does:
  1. Receives every scraped opportunity item from DedupePipeline
  2. Sends title + category + summary + deadline to Gemini 2.0 Flash
  3. Gemini returns: a relevance score (1–10) + a 2-sentence blurb
  4. Items scoring below MIN_SCORE (5) are dropped — never reach the sheet
  5. Items scoring 5+ get their AI Blurb stored in the sheet (column F)

Gemini model:  gemini-2.0-flash
API key:       GEMINI_API_KEY (GitHub Secret → wired into .env by scoutbot.yml)
Rate limiting: Semaphore(1) + 4-second sleep → stays within free-tier 15 RPM limit
Free tier:     1,500 requests/day — ScoutBot uses ~5–15/day

Where to find evidence of Gemini running:
  - GitHub Actions logs: search for "GeminiPipeline" in the "Run ScoutBot" step
  - Google Sheet: "AI Blurb" column (column F) in Nigeria / International tabs
  - Email digest: blurb text appears under each opportunity title

Pipeline order in scoutbot/settings.py:
  DedupePipeline (100) → GeminiPipeline (150) → SheetsPipeline (200)
"""

import json
import logging
import os
import re
import threading
import time
import urllib.request

from scrapy.exceptions import DropItem
from twisted.internet import defer, threads

logger = logging.getLogger(__name__)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.0-flash:generateContent"
)

# Minimum Gemini score to keep an item. Items scoring below this are silently dropped.
MIN_SCORE = 5

# Semaphore limits concurrent Gemini calls to 1 at a time.
# Combined with the 4-second sleep this keeps throughput at ~15 RPM —
# safely within Gemini's free-tier rate limit.
_GEMINI_SEM = threading.Semaphore(1)


class GeminiPipeline:
    """Scrapy pipeline — scores each opportunity with Gemini 2.0 Flash.

    Enabled only when GEMINI_API_KEY is set in the environment.
    If the key is missing or an API call fails, the item passes through with
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
        if self.enabled:
            logger.info("GeminiPipeline: AI scoring ENABLED (model: gemini-2.0-flash).")
        else:
            logger.warning(
                "GeminiPipeline: GEMINI_API_KEY not set — AI scoring DISABLED. "
                "Items will pass through with empty blurbs. "
                "Add GEMINI_API_KEY to GitHub Secrets to enable scoring."
            )

    @defer.inlineCallbacks
    def process_item(self, item, spider=None):
        if not self.enabled:
            item["ai_blurb"] = ""
            return item
        result = yield threads.deferToThread(self._call_gemini, item)
        return result

    def _call_gemini(self, item):
        """Rate-limited wrapper — always called inside _GEMINI_SEM."""
        with _GEMINI_SEM:
            time.sleep(4)   # 4s gap → ~15 RPM, within free-tier limit
            return self._call_gemini_inner(item)

    def _call_gemini_inner(self, item):
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

        try:
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 120},
            }).encode()
            req = urllib.request.Request(
                f"{GEMINI_URL}?key={self.api_key}",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as r:
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

        except DropItem:
            raise
        except Exception as exc:
            logger.warning(
                "GeminiPipeline: API error for \"%s\" — %s; passing through with empty blurb.",
                title[:60], exc,
            )
            item["ai_blurb"] = ""
            return item
