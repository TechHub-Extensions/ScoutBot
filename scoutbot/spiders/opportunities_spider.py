"""
ScoutBot main spider — fast, lightweight, students-only.

Sources:
  - Google News RSS (Nigeria + International searches)
  - YouthHubAfrica Nigeria tag page (direct HTML scrape)

Design philosophy (v2 — "direct RSS"):
  Items are emitted directly from RSS feed data, WITHOUT following article links.
  This means each run completes in < 60 seconds instead of 2+ minutes.

  The application_link is the RSS item link (news.google.com redirect) — these
  work correctly when clicked, taking the reader to the source article via Google
  News reader. No JavaScript or redirect-following is needed in Scrapy.

  Quality gating is handled entirely by GeminiPipeline (score >= 5), not by
  whether a direct apply URL can be extracted from an article page.
"""

import re
from datetime import date, timedelta

import scrapy

from scoutbot.items import OpportunityItem

try:
    from dateutil.parser import parse as dateutil_parse
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


CATEGORY_MAP = [
    ("scholarship", "Scholarship"),
    ("fellowships", "Fellowship"),
    ("fellowship", "Fellowship"),
    ("internship", "Internship"),
    ("internships", "Internship"),
    ("industrial training", "Internship"),
    ("bootcamp", "Bootcamp"),
    ("boot-camp", "Bootcamp"),
    ("coding camp", "Bootcamp"),
    ("apprentice", "Apprenticeship"),
    ("conference", "Conference"),
    ("summit", "Conference"),
    ("award", "Award"),
    ("competition", "Competition"),
    ("exchange", "Fellowship"),
    ("graduate programme", "Fellowship"),
    ("graduate program", "Fellowship"),
    ("programme", "Fellowship"),
    ("program", "Fellowship"),
    ("training", "Internship"),
]

INDUSTRY_KEYWORDS = {
    "Tech": ["tech", "software", "coding", "developer", "data", "ai", "digital",
             "fintech", "ict", "computer", "stem", "cyber", "programming",
             "machine learning", "saas", "deeptech", "web3", "blockchain"],
    "Engineering": ["engineer", "mechanical", "civil", "electrical", "petroleum",
                    "chemical", "structural", "architecture"],
    "Law": ["law", "legal", "justice", "llb", "llm", "barrister", "solicitor"],
    "Finance": ["finance", "accounting", "economics", "business",
                "commerce", "banking", "investment"],
    "Medicine": ["medicine", "health", "medical", "nursing", "pharma",
                 "biology", "public health", "research", "clinical"],
}

RANGE_KEYWORDS_INTL = [
    "international", "study abroad", "global", "worldwide", "overseas",
    "fulbright", " uk ", "usa", "europe", "canada", "australia",
    "china", "japan", "korea", "commonwealth", "world bank", " un ",
]

NIGERIA_CONTENT_KEYWORDS = [
    "nigeria", "nigerian", "nigerians",
    "lagos", "abuja", "kano", "ibadan", "port harcourt",
    "enugu", "benin city", "kaduna", "owerri",
    "open to nigerians", "for nigerians", "nigerian students",
]

PAST_YEAR_RE = re.compile(r"\b(202[0-4])\b")

MAX_POST_AGE_DAYS = 5   # drop RSS items older than this

# Title must contain at least one of these for the item to proceed to Gemini
TITLE_KEYWORDS = [
    "scholarship", "fellowship", "internship", "bootcamp",
    "training", "award", "programme", "program",
    "application", "apply", "funded", "bursary",
    "exchange", "competition", "apprenticeship",
]


def _infer_category(text):
    text = text.lower()
    for kw, cat in CATEGORY_MAP:
        if kw in text:
            return cat
    return "Opportunity"


def _infer_industry(text):
    text = text.lower()
    for ind, kws in INDUSTRY_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return ind
    return "General"


def _infer_range(text, forced=None):
    if forced:
        return forced
    text = text.lower()
    if any(kw in text for kw in RANGE_KEYWORDS_INTL):
        return "International"
    if any(kw in text for kw in NIGERIA_CONTENT_KEYWORDS):
        return "National"
    return "International"


def _extract_deadline(text):
    month_expr = (
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
        r"|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?"
        r"|nov(?:ember)?|dec(?:ember)?)"
    )
    date_expr = (
        rf"\d{{1,2}}(?:st|nd|rd|th)?\s+{month_expr}\s+\d{{4}}"
        rf"|{month_expr}\s+\d{{1,2}},?\s*\d{{4}}"
        rf"|\d{{1,2}}/\d{{1,2}}/\d{{4}}"
    )
    patterns = [
        rf"(?:deadline|apply\s+by|closes?|closing\s+date)[:\s]+({date_expr})",
        rf"({date_expr})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return next(g for g in m.groups() if g is not None).strip()
    if re.search(r"\brolling\b", text, re.IGNORECASE):
        return "Rolling"
    return ""


def _strip_html(text):
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _strip_source_suffix(title):
    """Google News titles end with ' - Source Name'. Remove that part."""
    return re.sub(r"\s*[-–—]\s*[A-Za-z0-9 ]+$", "", title).strip()


class OpportunitiesSpider(scrapy.Spider):
    name = "opportunities"

    # Direct HTML scrape — YouthHub has its own database with proper apply links
    start_urls = [
        "https://opportunities.youthhubafrica.org/tag/nigeria/",
    ]

    # Nigeria RSS queries
    GOOGLE_NEWS_RSS_NIGERIA = [
        "https://news.google.com/rss/search?q=nigeria+scholarship+2026&hl=en-NG&gl=NG&ceid=NG:en",
        "https://news.google.com/rss/search?q=nigeria+fellowship+2026&hl=en-NG&gl=NG&ceid=NG:en",
        "https://news.google.com/rss/search?q=nigeria+internship+2026&hl=en-NG&gl=NG&ceid=NG:en",
        "https://news.google.com/rss/search?q=nigeria+scholarship+OR+fellowship+2026&hl=en-NG&gl=NG&ceid=NG:en",
    ]

    # International RSS queries (routed to International tab)
    GOOGLE_NEWS_RSS_INTL = [
        "https://news.google.com/rss/search?q=commonwealth+scholarship+2026+Nigeria&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=international+fellowship+Africa+2026&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=fully+funded+scholarship+Nigeria+2026&hl=en&gl=US&ceid=US:en",
    ]

    def start_requests(self):
        yield scrapy.Request(self.start_urls[0], callback=self.parse_youthhubafrica)
        for url in self.GOOGLE_NEWS_RSS_NIGERIA:
            yield scrapy.Request(
                url, callback=self.parse_rss,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                meta={"forced_range": "National"},
            )
        for url in self.GOOGLE_NEWS_RSS_INTL:
            yield scrapy.Request(
                url, callback=self.parse_rss,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                meta={"forced_range": "International"},
            )

    # ── YouthHubAfrica (direct HTML scrape) ──────────────────────────────────

    def parse_youthhubafrica(self, response):
        """Scrape the YouthHubAfrica Nigeria listings page."""
        links = response.css(
            "article h2 a::attr(href), article h3 a::attr(href), "
            ".entry-title a::attr(href), h2.post-title a::attr(href)"
        ).getall()
        for link in links:
            if link and link.startswith("http") and "/20" in link:
                ym = PAST_YEAR_RE.search(link)
                if ym and int(ym.group(1)) < date.today().year:
                    continue
                yield scrapy.Request(
                    link, callback=self.parse_youthhubafrica_article,
                    meta={"forced_range": "National"},
                )

    def parse_youthhubafrica_article(self, response):
        title = response.css("h1::text").get("").strip()
        if not title:
            return
        ym = PAST_YEAR_RE.search(title)
        if ym and int(ym.group(1)) < date.today().year:
            return

        body = " ".join(response.css(
            "article p::text, .entry-content p::text, .post-content p::text"
        ).getall())
        combined = title + " " + body

        # Direct apply link from the article page
        apply_link = (
            response.css(
                "a[href*='apply']::attr(href), "
                "a[href*='application']::attr(href), "
                ".wp-block-button a::attr(href)"
            ).get("")
            or response.url
        )

        deadline = _extract_deadline(combined)
        category = _infer_category(combined)

        item = OpportunityItem()
        item["title"]            = title
        item["industry"]         = _infer_industry(combined)
        item["category"]         = category
        item["range"]            = "National"
        item["education_level"]  = ""
        item["organization"]     = "YouthHubAfrica"
        item["summary"]          = body[:400].strip()
        item["application_link"] = apply_link
        item["opening_date"]     = ""
        item["deadline"]         = deadline
        item["status"]           = "Open"
        yield item

    # ── Google News RSS (emit items directly, NO article fetching) ───────────

    def parse_rss(self, response):
        """Parse Google News RSS feed and emit items directly without following links.

        Items are emitted from the RSS data itself (title + description snippet).
        No article pages are fetched — this keeps the run time under 60 seconds.
        GeminiPipeline acts as the quality gate (score >= 5 required).
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(response.text)
        except Exception as exc:
            self.logger.warning("RSS parse failed — %s", exc)
            return

        channel = root.find("channel")
        if channel is None:
            return

        cutoff    = date.today() - timedelta(days=MAX_POST_AGE_DAYS)
        forced    = response.meta.get("forced_range", "National")
        emitted   = 0

        for entry in channel.findall("item"):
            raw_title = (entry.findtext("title") or "").strip()
            if not raw_title:
                continue

            # Strip " - Source Name" suffix that Google News appends
            title = _strip_source_suffix(raw_title)

            # Require a recognisable opportunity keyword in the title
            if not any(kw in title.lower() for kw in TITLE_KEYWORDS):
                continue

            # Drop past-year titles
            ym = PAST_YEAR_RE.search(title)
            if ym and int(ym.group(1)) < date.today().year:
                continue

            # Drop if post is too old
            pub_date = entry.findtext("pubDate") or ""
            if pub_date and HAS_DATEUTIL:
                try:
                    pub = dateutil_parse(pub_date, fuzzy=True).date()
                    if pub < cutoff:
                        continue
                except Exception:
                    pass

            link = (entry.findtext("link") or "").strip()
            if not link:
                continue

            # Description snippet (may contain HTML tags)
            raw_desc = entry.findtext("description") or ""
            summary  = _strip_html(raw_desc)[:400]

            combined  = title + " " + summary
            category  = _infer_category(combined)
            range_val = _infer_range(combined, forced)
            deadline  = _extract_deadline(combined)

            # Source organisation from <source url="..."> element
            src_el = entry.find("source")
            org    = src_el.text.strip() if src_el is not None and src_el.text else ""

            item = OpportunityItem()
            item["title"]            = title
            item["industry"]         = _infer_industry(combined)
            item["category"]         = category
            item["range"]            = range_val
            item["education_level"]  = ""
            item["organization"]     = org
            item["summary"]          = summary
            item["application_link"] = link
            item["opening_date"]     = ""
            item["deadline"]         = deadline
            item["status"]           = "Open"

            emitted += 1
            yield item

        self.logger.info(
            "RSS (%s…): %d items emitted.",
            response.url[-55:], emitted,
        )
