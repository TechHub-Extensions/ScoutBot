"""
ScoutBot opportunities spider — v5 "Nigerian source sites"

Problem with Google News: CBMi links need JavaScript to resolve → can't get real URLs.
Problem with major aggregators (opportunitydesk.org, afterschoolafrica.com):
  Cloudflare blocks GitHub Actions datacenter IPs → 403 on RSS and articles.

Solution: Use Nigerian news/education sites that:
  a) Are NOT Cloudflare-blocked from GitHub Actions
  b) Have RSS feeds with real article URLs
  c) Cover scholarships, fellowships, and internships
  d) Have "Apply Here" buttons in their articles pointing to org websites

Primary RSS sources (verified accessible, real article URLs):
  - edugist.org           — Nigeria's education news site, covers GTBank/MTN/etc internships
  - encomium.ng           — Nigerian news, regularly covers MTN/corporate scholarships
  - msmeafricaonline.com  — Business/MSME news, covers Mastercard Foundation etc.
  - investorsking.com     — Investment/opportunity news
  - scholars4dev.com      — Scholarship aggregator, accessible, direct article URLs

Secondary: curated direct org pages (no Cloudflare, open org website URLs):
  - Tony Elumelu Foundation, MTN Foundation, PTDF, World Bank, AU, UNDP, etc.

Only three accepted categories: Scholarship, Fellowship, Internship.
"""

import re
from datetime import date, timedelta
from urllib.parse import urlparse, urljoin

import scrapy

from scoutbot.items import OpportunityItem

try:
    from dateutil.parser import parse as dateutil_parse
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


# ── Category / classification helpers ─────────────────────────────────────────

ACCEPTED_CATEGORIES = {"Scholarship", "Fellowship", "Internship"}

CATEGORY_MAP = [
    ("scholarship", "Scholarship"),
    ("bursary",     "Scholarship"),
    ("grant",       "Scholarship"),
    ("funded",      "Scholarship"),
    ("fellowship",  "Fellowship"),
    ("exchange programme", "Fellowship"),
    ("exchange program",   "Fellowship"),
    ("residency",   "Fellowship"),
    ("internship",  "Internship"),
    ("industrial training", "Internship"),
    ("graduate trainee",    "Internship"),
    ("apprenticeship",      "Internship"),
    ("summership",          "Internship"),
    ("graduate programme",  "Fellowship"),
    ("graduate program",    "Fellowship"),
]

TITLE_KEYWORDS = [
    "scholarship", "fellowship", "internship", "bursary", "funded",
    "exchange programme", "exchange program", "graduate trainee",
    "industrial training", "apprenticeship", "summership",
]

PAST_YEAR_RE = re.compile(r"\b(202[0-4])\b")
MAX_POST_AGE = 14   # days

NIGERIA_SIGNALS = [
    "nigeria", "nigerian", "nigerians", "lagos", "abuja", "kano", "ibadan",
    "enugu", "owerri", "for nigerians", "open to nigerians", "naija",
]
INTL_SIGNALS = [
    "international", "study abroad", "global", "worldwide", "overseas",
    "fulbright", "commonwealth", "world bank", "united nations", " un ",
    "african union", "africa", "daad", "erasmus", "chevening", "mastercard",
    "fully funded", "funded scholarship",
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


def _infer_category(text: str):
    t = text.lower()
    for kw, cat in CATEGORY_MAP:
        if kw in t:
            return cat
    return None


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
    for p in [
        rf"(?:deadline|closes?|apply\s+by|closing\s+date)[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\s+\d{{4}})",
        rf"(?:deadline|closes?|apply\s+by)[:\s]+({month}\s+\d{{1,2}},?\s*\d{{4}})",
        rf"(\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\s+\d{{4}})",
        rf"({month}\s+\d{{1,2}},?\s*\d{{4}})",
    ]:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return "Rolling" if re.search(r"\brolling\b", text, re.IGNORECASE) else ""


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    for e, c in [("&amp;","&"),("&lt;","<"),("&gt;",">"),
                 ("&quot;",'"'),("&#39;","'"),("&nbsp;"," ")]:
        text = text.replace(e, c)
    return re.sub(r"\s+", " ", text).strip()


def _is_external(href: str, base_netloc: str) -> bool:
    if not href or not href.startswith("http"):
        return False
    return urlparse(href).netloc not in ("", base_netloc)


def _extract_apply_link(response, fallback: str) -> str:
    """
    Find the real org application link from a news/aggregator article page.

    Priority:
    1. WordPress button blocks (most reliable on aggregator sites)
    2. Links with apply/register/official text pointing to external domains
    3. External links with apply/careers/form/vacancy in href
    4. Fall back to the article URL (response.url or fallback)
    """
    base = urlparse(response.url).netloc

    # 1. WordPress / Elementor / theme button blocks
    for sel in [
        ".wp-block-button a::attr(href)",
        ".wp-block-button__link::attr(href)",
        ".elementor-button::attr(href)",
        ".et_pb_button::attr(href)",
        "a.button::attr(href)",
        "a.btn-primary::attr(href)",
        "a.btn-default::attr(href)",
    ]:
        for href in response.css(sel).getall():
            if _is_external(href, base):
                return href

    # 2. Links with apply/register/official text
    APPLY_TEXTS = {
        "apply here", "apply now", "click here to apply", "apply online",
        "apply for this", "start application", "apply via", "apply",
        "register here", "register now", "official website",
        "application form", "application portal", "here to apply",
        "application link", "click to apply", "application page",
        "apply for scholarship", "apply for fellowship", "apply for internship",
    }
    for a in response.css(
        ".entry-content a, .post-content a, article a, .content a, "
        ".td-post-content a, .entry a, .article-body a"
    ):
        href = a.attrib.get("href", "")
        if not _is_external(href, base):
            continue
        text = " ".join(a.css("::text").getall()).lower().strip()
        if any(kw in text for kw in APPLY_TEXTS):
            return href

    # 3. External links with apply/careers/form in href
    for href in response.css(
        ".entry-content a::attr(href), .post-content a::attr(href), "
        "article a::attr(href), .td-post-content a::attr(href), "
        ".entry a::attr(href)"
    ).getall():
        if not _is_external(href, base):
            continue
        low = href.lower()
        if any(s in low for s in ["apply", "application", "careers", "vacancy",
                                   "register", "enroll", "scholarship", "fellowship"]):
            return href

    return fallback  # article URL on the news site (still real + human-readable)


# ── RSS source registry ───────────────────────────────────────────────────────
#
# These are Nigerian news/education sites that:
# - Have RSS feeds with REAL article URLs (not news.google.com/CBMi)
# - Are accessible from GitHub Actions (no heavy Cloudflare)
# - Publish articles about scholarships, fellowships, internships
#
# (url, default_range_override)
# range=None → auto-detected from content

RSS_SOURCES = [
    # edugist.org — Nigeria's education news, covers GTBank/MTN/Shell internships
    ("https://edugist.org/feed/",                              None),
    # encomium.ng — covers MTN Foundation, corporate scholarships
    ("https://encomium.ng/feed/",                              None),
    # msmeafricaonline.com — Mastercard Foundation, SMEDAN grants, fellowships
    ("https://msmeafricaonline.com/feed/",                     None),
    # investorsking.com — Canada/UK/international scholarships for Nigerians
    ("https://investorsking.com/feed/",                        None),
    # scholars4dev.com — dedicated scholarship site, real article URLs
    ("https://www.scholars4dev.com/category/scholarships-for-africans/feed/",  "International"),
    ("https://www.scholars4dev.com/tag/nigeria/feed/",          "National"),
]

# ── Direct org pages (always correct, org-hosted URLs) ───────────────────────
DIRECT_PAGES = [
    {
        "url":        "https://tefffoundation.org/entrepreneurship-programme/",
        "org":        "Tony Elumelu Foundation",
        "range":      "National",
        "category":   "Fellowship",
        "title":      "Tony Elumelu Entrepreneurship Programme 2026",
        "apply_link": "https://tefffoundation.org/entrepreneurship-programme/apply/",
    },
    {
        "url":        "https://mtnfoundation.org.ng/scholarships/",
        "org":        "MTN Foundation",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "MTN Foundation Scholarship 2026",
        "apply_link": "https://mtnfoundation.org.ng/scholarships/",
    },
    {
        "url":        "https://www.ptdf.gov.ng/scholarships/",
        "org":        "PTDF",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "PTDF Scholarship 2025/2026",
        "apply_link": "https://www.ptdf.gov.ng/scholarships/",
    },
    {
        "url":        "https://nddc.gov.ng/media-room/news/",
        "org":        "NDDC",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "NDDC Postgraduate Scholarship 2026",
        "apply_link": "https://nddc.gov.ng/scholarships/",
    },
    {
        "url":        "https://www.worldbank.org/en/programs/scholarships",
        "org":        "World Bank",
        "range":      "International",
        "category":   "Scholarship",
        "title":      "World Bank Scholarship Programs",
        "apply_link": "https://www.worldbank.org/en/programs/scholarships",
    },
    {
        "url":        "https://au.int/en/internship",
        "org":        "African Union",
        "range":      "International",
        "category":   "Internship",
        "title":      "African Union Internship Programme 2026",
        "apply_link": "https://au.int/en/internship",
    },
    {
        "url":        "https://cscuk.fcdo.gov.uk/apply/",
        "org":        "Commonwealth Scholarship Commission",
        "range":      "International",
        "category":   "Scholarship",
        "title":      "Commonwealth Scholarship 2026/27",
        "apply_link": "https://cscuk.fcdo.gov.uk/apply/",
    },
    {
        "url":        "https://www.chevening.org/scholarships/",
        "org":        "Chevening Scholarships",
        "range":      "International",
        "category":   "Scholarship",
        "title":      "Chevening Scholarship 2026/2027",
        "apply_link": "https://www.chevening.org/apply/",
    },
]


# ── Spider ────────────────────────────────────────────────────────────────────

class OpportunitiesSpider(scrapy.Spider):
    name = "opportunities"

    custom_settings = {
        "DOWNLOAD_TIMEOUT":        20,
        "RETRY_TIMES":              1,
        "HTTPERROR_ALLOWED_CODES": [403, 429, 503],
    }

    def start_requests(self):
        for url, range_override in RSS_SOURCES:
            yield scrapy.Request(
                url, callback=self.parse_rss,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                meta={"range_override": range_override},
                errback=self.errback_rss,
            )
        for cfg in DIRECT_PAGES:
            yield scrapy.Request(
                cfg["url"], callback=self.parse_direct,
                meta={"cfg": cfg},
                errback=self.errback_direct,
            )

    # ── RSS (supports both RSS 2.0 and Atom) ──────────────────────────────────

    def parse_rss(self, response):
        import xml.etree.ElementTree as ET

        if response.status != 200:
            self.logger.warning("RSS %s → HTTP %s", response.url, response.status)
            return

        try:
            root = ET.fromstring(response.text)
        except Exception as exc:
            self.logger.warning("Feed parse error: %s", exc)
            return

        range_override = response.meta.get("range_override")
        cutoff         = date.today() - timedelta(days=MAX_POST_AGE)

        # Detect RSS 2.0 vs Atom
        channel = root.find("channel")
        if channel is not None:
            entries = channel.findall("item")
            def _t(e): return (e.findtext("title") or "").strip()
            def _l(e): return (e.findtext("link") or "").strip()
            def _d(e): return _strip_html(e.findtext("description") or "")
            def _p(e): return (e.findtext("pubDate") or "").strip()
        else:
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
            def _t(e): return (e.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            def _l(e):
                for lnk in e.findall("{http://www.w3.org/2005/Atom}link"):
                    if lnk.get("rel", "alternate") == "alternate":
                        return lnk.get("href", "")
                return ""
            def _d(e): return _strip_html(
                e.findtext("{http://www.w3.org/2005/Atom}summary") or
                e.findtext("{http://www.w3.org/2005/Atom}content") or "")
            def _p(e): return (e.findtext("{http://www.w3.org/2005/Atom}published") or "").strip()

        queued = 0
        for entry in entries:
            title = _t(entry)
            if not title:
                continue

            title_lower = title.lower()
            if not any(kw in title_lower for kw in TITLE_KEYWORDS):
                continue

            category = _infer_category(title_lower)
            if category not in ACCEPTED_CATEGORIES:
                continue

            ym = PAST_YEAR_RE.search(title)
            if ym and int(ym.group(1)) < date.today().year:
                continue

            pub = _p(entry)
            if pub and HAS_DATEUTIL:
                try:
                    if dateutil_parse(pub, fuzzy=True).date() < cutoff:
                        continue
                except Exception:
                    pass

            link = _l(entry)
            if not link or not link.startswith("http"):
                continue

            desc     = _d(entry)[:400]
            combined = title + " " + desc

            item = OpportunityItem()
            item["title"]            = title
            item["industry"]         = _infer_industry(combined)
            item["category"]         = category
            item["range"]            = _infer_range(combined, range_override)
            item["education_level"]  = ""
            item["organization"]     = ""
            item["summary"]          = desc
            item["application_link"] = link   # real article URL — upgraded in parse_article
            item["opening_date"]     = ""
            item["deadline"]         = _extract_deadline(combined)
            item["status"]           = "Open"

            queued += 1
            yield scrapy.Request(
                link, callback=self.parse_article,
                errback=self.errback_article,
                headers={"Referer": response.url},
                meta={"item": item},
            )

        self.logger.info("RSS %.55s…: %d items queued.", response.url, queued)

    # ── Article page — extract the real org "Apply" link ──────────────────────

    def parse_article(self, response):
        item = response.meta["item"]
        article_url = response.url   # real article URL on news site

        if response.status in (403, 429, 503):
            # Keep the article URL — still better than news.google.com
            self.logger.debug("Article %s → %s — keeping article URL.", article_url, response.status)
            yield item
            return

        # Upgrade application_link: try to extract the org's apply button
        apply_link = _extract_apply_link(response, fallback=article_url)
        item["application_link"] = apply_link

        # Upgrade deadline from full article body
        if not item.get("deadline"):
            body = " ".join(response.css(
                ".entry-content *::text, .post-content *::text, "
                "article *::text, .td-post-content *::text"
            ).getall())
            item["deadline"] = _extract_deadline(body)

        # Set org name from apply link domain (if different from article site)
        if not item.get("organization"):
            apply_netloc = urlparse(apply_link).netloc
            art_netloc   = urlparse(article_url).netloc
            if apply_netloc and apply_netloc != art_netloc:
                item["organization"] = apply_netloc.replace("www.", "")
            else:
                # Fall back to the news site name
                item["organization"] = art_netloc.replace("www.", "")

        yield item

    def errback_article(self, failure):
        item = failure.request.meta.get("item")
        if item:
            self.logger.debug("Article %s failed — keeping article URL.", failure.request.url)
            yield item

    def errback_rss(self, failure):
        self.logger.warning("RSS failed: %s — %s", failure.request.url, failure.value)

    # ── Direct org pages ──────────────────────────────────────────────────────

    def parse_direct(self, response):
        cfg = response.meta["cfg"]
        if response.status in (403, 429, 503):
            yield self._direct_item(cfg, body="")
            return

        body = " ".join(response.css("*::text").getall())
        OPEN = ["apply", "applications open", "accepting applications",
                "deadline", "apply now", "now open", "accepting entries"]
        if not any(s in body.lower() for s in OPEN):
            self.logger.info("Direct page %s shows no open opportunity — skipping.", cfg["url"])
            return

        # Try to find a better specific apply link on the page
        apply_link = cfg["apply_link"]
        for a in response.css("a"):
            href = a.attrib.get("href", "")
            text = " ".join(a.css("::text").getall()).lower()
            if any(kw in text for kw in ["apply now", "apply here", "application form"]):
                if href.startswith("http"):
                    apply_link = href
                    break
                elif href.startswith("/"):
                    apply_link = urljoin(response.url, href)
                    break

        yield self._direct_item(cfg, body=body[:400], apply_link=apply_link)

    def _direct_item(self, cfg, body="", apply_link=None):
        combined = cfg["title"] + " " + body
        item = OpportunityItem()
        item["title"]            = cfg["title"]
        item["industry"]         = _infer_industry(combined)
        item["category"]         = cfg["category"]
        item["range"]            = cfg["range"]
        item["education_level"]  = ""
        item["organization"]     = cfg["org"]
        item["summary"]          = body[:300].strip()
        item["application_link"] = apply_link or cfg["apply_link"]
        item["opening_date"]     = ""
        item["deadline"]         = _extract_deadline(body)
        item["status"]           = "Open"
        return item

    def errback_direct(self, failure):
        cfg = failure.request.meta.get("cfg", {})
        if cfg:
            yield self._direct_item(cfg, body="")
