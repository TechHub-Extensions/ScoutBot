"""
ScoutBot opportunities spider — v3 "direct links"

Sources (all three are opportunity aggregators, not news sites):
  - opportunitydesk.org  — Nigeria's largest opportunity aggregator
  - scholars4dev.com     — scholarship/fellowship focused
  - afterschoolafrica.com — Africa-wide

Design:
  1. Fetch RSS from each source (RSS feeds are not Cloudflare-protected)
  2. For each qualifying item, follow the article link on the aggregator site
  3. Extract the "Apply Here" / "Apply Now" button → this is the real org URL
  4. If the article page returns 403/timeout (Cloudflare), fall back to the
     aggregator article URL — still a real, human-readable page, not news.google.com
  5. Items pass to GeminiPipeline for scoring (score < 5 = dropped)

Only these three categories are accepted: Scholarship, Fellowship, Internship.
"""

import re
from datetime import date, timedelta
from urllib.parse import urlparse

import scrapy

from scoutbot.items import OpportunityItem

try:
    from dateutil.parser import parse as dateutil_parse
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


# ── Constants ─────────────────────────────────────────────────────────────────

ACCEPTED_CATEGORIES = {"Scholarship", "Fellowship", "Internship"}

CATEGORY_MAP = [
    ("scholarship", "Scholarship"),
    ("bursary",     "Scholarship"),
    ("grant",       "Scholarship"),
    ("fellowship",  "Fellowship"),
    ("exchange",    "Fellowship"),
    ("residency",   "Fellowship"),
    ("internship",  "Internship"),
    ("industrial training", "Internship"),
    ("graduate trainee",    "Internship"),
    ("graduate programme",  "Fellowship"),
    ("graduate program",    "Fellowship"),
]

TITLE_KEYWORDS = [
    "scholarship", "fellowship", "internship", "bursary", "grant",
    "exchange programme", "graduate trainee", "industrial training",
]

PAST_YEAR_RE   = re.compile(r"\b(202[0-4])\b")
MAX_POST_AGE   = 10   # days

NIGERIA_SIGNALS = [
    "nigeria", "nigerian", "nigerians", "lagos", "abuja", "kano", "ibadan",
    "enugu", "owerri", "open to nigerians", "for nigerians",
]

INTL_SIGNALS = [
    "international", "study abroad", "global", "worldwide", "overseas",
    "fulbright", "commonwealth", "world bank", "united nations", " un ",
    "african union", "africa", "daad", "erasmus", "chevening",
]

INDUSTRY_MAP = {
    "Tech":        ["tech", "software", "coding", "developer", "data", "ai",
                    "digital", "ict", "computer", "stem", "cyber", "fintech",
                    "machine learning", "blockchain", "web3"],
    "Engineering": ["engineer", "mechanical", "civil", "electrical", "petroleum",
                    "chemical", "structural", "architecture"],
    "Medicine":    ["medicine", "health", "medical", "nursing", "pharma",
                    "biology", "public health", "clinical"],
    "Finance":     ["finance", "accounting", "economics", "business",
                    "commerce", "banking", "investment"],
    "Law":         ["law", "legal", "llb", "llm", "barrister", "solicitor"],
}

# ── RSS feed registry ─────────────────────────────────────────────────────────
#
# (url, default_range_override_or_None)
# range=None means auto-detect from content
#
RSS_FEEDS = [
    # opportunitydesk.org — Nigeria-focused aggregator
    ("https://opportunitydesk.org/category/nigeria/feed/",            "National"),
    ("https://opportunitydesk.org/category/scholarships-2/feed/",     None),
    ("https://opportunitydesk.org/category/fellowships-2/feed/",      None),
    ("https://opportunitydesk.org/category/internships-2/feed/",      None),

    # scholars4dev.com — international scholarships open to Africans
    ("https://scholars4dev.com/category/scholarship-by-location/africa-scholarships/feed/", "International"),
    ("https://scholars4dev.com/category/fellowships/feed/",           "International"),
    ("https://scholars4dev.com/category/internships/feed/",           "International"),

    # afterschoolafrica.com — Africa-wide
    ("https://afterschoolafrica.com/category/scholarships/feed/",     "International"),
    ("https://afterschoolafrica.com/category/fellowships/feed/",      "International"),
    ("https://afterschoolafrica.com/category/internships/feed/",      "International"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_category(text: str) -> str:
    t = text.lower()
    for kw, cat in CATEGORY_MAP:
        if kw in t:
            return cat
    return None   # None means "reject" — not an accepted category


def _infer_range(text: str, override=None) -> str:
    if override:
        return override
    t = text.lower()
    if any(s in t for s in NIGERIA_SIGNALS):
        return "National"
    if any(s in t for s in INTL_SIGNALS):
        return "International"
    return "International"


def _infer_industry(text: str) -> str:
    t = text.lower()
    for ind, kws in INDUSTRY_MAP.items():
        if any(kw in t for kw in kws):
            return ind
    return "General"


def _extract_deadline(text: str) -> str:
    month = (
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
        r"|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?"
        r"|nov(?:ember)?|dec(?:ember)?)"
    )
    patterns = [
        rf"(?:deadline|closes?|apply\s+by|closing\s+date)[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\s+\d{{4}})",
        rf"(?:deadline|closes?|apply\s+by|closing\s+date)[:\s]+({month}\s+\d{{1,2}},?\s*\d{{4}})",
        rf"(\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\s+\d{{4}})",
        rf"({month}\s+\d{{1,2}},?\s*\d{{4}})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    if re.search(r"\brolling\b", text, re.IGNORECASE):
        return "Rolling"
    return ""


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    for ent, ch in [("&amp;","&"),("&lt;","<"),("&gt;",">"),
                    ("&quot;",'"'),("&#39;","'"),("&nbsp;"," ")]:
        text = text.replace(ent, ch)
    return re.sub(r"\s+", " ", text).strip()


def _extract_apply_link(response) -> str:
    """
    Walk the article page looking for the real organisation application URL.
    Priority order:
      1. WordPress button block links to external domains (most reliable)
      2. Any link whose visible text contains apply/register/official keywords
         and points to an external domain
      3. External links whose href contains apply/application/careers/form
      4. Fall back to the aggregator article URL (response.url)
    """
    base = urlparse(response.url).netloc

    def is_external(href: str) -> bool:
        if not href or not href.startswith("http"):
            return False
        return urlparse(href).netloc not in ("", base)

    # 1. WordPress / Elementor / Divi button blocks
    button_selectors = (
        ".wp-block-button a::attr(href)",
        ".wp-block-button__link::attr(href)",
        ".elementor-button::attr(href)",
        ".et_pb_button::attr(href)",
        "a.button::attr(href)",
        "a.btn::attr(href)",
    )
    for sel in button_selectors:
        for href in response.css(sel).getall():
            if is_external(href):
                return href

    # 2. Links with apply/register text in article body
    APPLY_TEXTS = {
        "apply here", "apply now", "click here to apply", "apply online",
        "apply for this", "start application", "begin application",
        "register here", "register now", "official website",
        "application form", "application portal", "apply via",
    }
    for a in response.css(".entry-content a, .post-content a, article a, .content a"):
        href = a.attrib.get("href", "")
        if not is_external(href):
            continue
        link_text = " ".join(a.css("::text").getall()).lower().strip()
        if any(kw in link_text for kw in APPLY_TEXTS):
            return href

    # 3. External links with apply/careers/form in href
    APPLY_HREF_SIGNALS = ["apply", "application", "careers", "vacancy", "form", "register"]
    for href in response.css(
        ".entry-content a::attr(href), .post-content a::attr(href), article a::attr(href)"
    ).getall():
        if not is_external(href):
            continue
        href_lower = href.lower()
        if any(s in href_lower for s in APPLY_HREF_SIGNALS):
            return href

    return response.url   # fallback: aggregator article page


# ── Spider ────────────────────────────────────────────────────────────────────

class OpportunitiesSpider(scrapy.Spider):
    name = "opportunities"

    custom_settings = {
        # Override global settings for this spider only
        "DOWNLOAD_TIMEOUT":  20,
        "RETRY_TIMES":        1,
        # Accept 403 in the callback so we can handle Cloudflare gracefully
        "HTTPERROR_ALLOWED_CODES": [403, 429, 503],
    }

    def start_requests(self):
        for url, range_override in RSS_FEEDS:
            yield scrapy.Request(
                url,
                callback=self.parse_rss,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                meta={"range_override": range_override, "dont_redirect": False},
                # Don't raise on RSS 404 — just log and continue
                errback=self.errback_rss,
            )

    def errback_rss(self, failure):
        self.logger.warning("RSS feed failed: %s — %s", failure.request.url, failure.value)

    # ── Parse RSS feed ────────────────────────────────────────────────────────

    def parse_rss(self, response):
        import xml.etree.ElementTree as ET

        if response.status != 200:
            self.logger.warning("RSS %s returned HTTP %s — skipping.", response.url, response.status)
            return

        try:
            root = ET.fromstring(response.text)
        except Exception as exc:
            self.logger.warning("RSS parse error at %s — %s", response.url, exc)
            return

        channel = root.find("channel")
        if channel is None:
            return

        cutoff         = date.today() - timedelta(days=MAX_POST_AGE)
        range_override = response.meta.get("range_override")
        emitted        = 0

        for entry in channel.findall("item"):
            title = (entry.findtext("title") or "").strip()
            if not title:
                continue

            # Must contain a qualifying keyword
            title_lower = title.lower()
            if not any(kw in title_lower for kw in TITLE_KEYWORDS):
                continue

            # Must map to an accepted category
            category = _infer_category(title_lower)
            if category not in ACCEPTED_CATEGORIES:
                continue

            # Drop titles mentioning past years (2020–2024)
            ym = PAST_YEAR_RE.search(title)
            if ym and int(ym.group(1)) < date.today().year:
                continue

            # Drop stale items
            pub_date = entry.findtext("pubDate") or ""
            if pub_date and HAS_DATEUTIL:
                try:
                    if dateutil_parse(pub_date, fuzzy=True).date() < cutoff:
                        continue
                except Exception:
                    pass

            article_url = (entry.findtext("link") or "").strip()
            if not article_url or not article_url.startswith("http"):
                continue

            raw_desc = entry.findtext("description") or ""
            summary  = _strip_html(raw_desc)[:400]
            combined = title + " " + summary

            # Source org from <source url="..."> element
            src_el = entry.find("source")
            org    = src_el.text.strip() if (src_el is not None and src_el.text) else ""

            # Build a partial item — application_link filled in parse_article
            item = OpportunityItem()
            item["title"]            = title
            item["industry"]         = _infer_industry(combined)
            item["category"]         = category
            item["range"]            = _infer_range(combined, range_override)
            item["education_level"]  = ""
            item["organization"]     = org
            item["summary"]          = summary
            item["application_link"] = article_url   # will be upgraded in parse_article
            item["opening_date"]     = ""
            item["deadline"]         = _extract_deadline(combined)
            item["status"]           = "Open"

            emitted += 1
            yield scrapy.Request(
                article_url,
                callback=self.parse_article,
                errback=self.errback_article,
                headers={"Referer": "https://www.google.com/"},
                meta={"item": item},
                # Don't cache — we want fresh apply links
                dont_filter=False,
            )

        self.logger.info(
            "RSS %.55s…: %d qualifying items queued.", response.url, emitted
        )

    # ── Parse article page — extract real org apply link ─────────────────────

    def parse_article(self, response):
        item = response.meta["item"]

        # Cloudflare / rate-limited — fall back to the aggregator article URL
        if response.status in (403, 429, 503):
            self.logger.debug(
                "Article %s returned HTTP %s — using aggregator URL as apply link.",
                response.url, response.status,
            )
            yield item
            return

        # Try to extract a better org-level apply link from the page
        apply_link = _extract_apply_link(response)
        item["application_link"] = apply_link

        # Upgrade deadline from full article body if RSS snippet was empty
        if not item.get("deadline"):
            body = " ".join(response.css(
                ".entry-content *::text, .post-content *::text, article *::text"
            ).getall())
            item["deadline"] = _extract_deadline(body)

        # Upgrade org name from page if RSS <source> was empty
        if not item.get("organization"):
            parsed = urlparse(apply_link if apply_link != response.url else "")
            if parsed.netloc:
                item["organization"] = parsed.netloc.replace("www.", "")

        yield item

    def errback_article(self, failure):
        """Network error fetching article — yield item with aggregator article URL."""
        item = failure.request.meta.get("item")
        if item:
            self.logger.debug(
                "Article %s failed (%s) — using aggregator URL.",
                failure.request.url, failure.value,
            )
            yield item
