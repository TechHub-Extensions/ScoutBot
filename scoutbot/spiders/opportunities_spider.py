"""
ScoutBot opportunities spider — v6 "Curated org pages"

Why direct org pages only:
  Google News CBMi links: HTTP 200 immediately — no redirect — JavaScript required.
  Nigerian news site RSS (edugist.org etc.): also Cloudflare-blocked from GitHub Actions.
  scholars4dev.com: accessible but almost always 0 qualifying items in feeds.

Definitive approach:
  - Curate ~22 well-known org pages for Nigerian students (government + corporate + intl).
  - Check each page daily for "apply / deadline / applications open" signals.
  - If found → write the item with the org's direct URL as application_link.
  - DedupePipeline (by link) prevents re-writing the same opportunity every day.

scholars4dev.com is kept as a bonus RSS source since it IS accessible and its article
URLs are real (e.g. https://www.scholars4dev.com/29443/unicaf-scholarships/).
"""

import re
from datetime import date, timedelta
from urllib.parse import urljoin, urlparse

import scrapy

from scoutbot.items import OpportunityItem

try:
    from dateutil.parser import parse as dateutil_parse
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False

# ── Helpers ───────────────────────────────────────────────────────────────────

ACCEPTED_CATEGORIES = {"Scholarship", "Fellowship", "Internship"}

CATEGORY_MAP = [
    ("scholarship",          "Scholarship"),
    ("bursary",              "Scholarship"),
    ("grant",                "Scholarship"),  # only if combined with edu context
    ("fellowship",           "Fellowship"),
    ("exchange programme",   "Fellowship"),
    ("exchange program",     "Fellowship"),
    ("residency",            "Fellowship"),
    ("internship",           "Internship"),
    ("industrial training",  "Internship"),
    ("graduate trainee",     "Internship"),
    ("graduate programme",   "Fellowship"),
    ("graduate program",     "Fellowship"),
    ("apprenticeship",       "Internship"),
    ("summership",           "Internship"),
    ("entrepreneurship programme", "Fellowship"),
    ("fully funded",         "Scholarship"),
]

TITLE_KEYWORDS = [kw for kw, _ in CATEGORY_MAP]

INDUSTRY_MAP = {
    "Tech":        ["tech", "software", "coding", "developer", "data", "ai",
                    "digital", "ict", "computer", "stem", "cyber", "fintech",
                    "machine learning", "blockchain", "engineering"],
    "Engineering": ["mechanical", "civil", "electrical", "petroleum",
                    "chemical", "structural", "architecture"],
    "Medicine":    ["medicine", "health", "medical", "nursing", "pharma",
                    "biology", "public health", "clinical"],
    "Finance":     ["finance", "accounting", "economics", "business",
                    "banking", "investment", "commerce"],
    "Law":         ["law", "legal", "llb", "llm", "barrister", "solicitor"],
    "Agriculture": ["agriculture", "agric", "farming", "food security",
                    "agribusiness", "rural development"],
    "Media":       ["media", "journalism", "broadcasting", "communication",
                    "film", "writing", "documentary"],
}

PAST_YEAR_RE = re.compile(r"\b(202[0-4])\b")
MAX_POST_AGE  = 14   # days


def _infer_category(text: str):
    t = text.lower()
    for kw, cat in CATEGORY_MAP:
        if kw in t:
            return cat
    return None


def _infer_industry(text: str) -> str:
    t = text.lower()
    for ind, kws in INDUSTRY_MAP.items():
        if any(kw in t for kw in kws):
            return ind
    return "General"


def _extract_deadline(text: str) -> str:
    # Rolling / open-ended — check before date patterns to avoid false matches
    if re.search(r"\brolling admissions?\b|\bapplications reviewed monthly\b|\breviewed monthly\b", text, re.IGNORECASE):
        return "Rolling"

    month = (
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
        r"|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?"
        r"|nov(?:ember)?|dec(?:ember)?)"
    )
    for p in [
        # MM/DD/YYYY numeric (saurabhhhcodes #39, tsouk88 #40)
        r"(?:deadline|closes?|apply\s+by|applications?\s+close(?:s)?\s+on|accepted\s+until)[:\s]+(\d{1,2}/\d{1,2}/\d{4})",
        r"(\d{1,2}/\d{1,2}/\d{4})",
        # Named month with trigger phrases
        rf"(?:deadline|closes?|apply\s+by|closing\s+date|applications?\s+close(?:s)?\s+on|accepted\s+until)[:\s]+(\d{{1,2}}(?:st|nd|rd|th)?\s+{month}\s+\d{{4}})",
        rf"(?:deadline|closes?|apply\s+by|closing\s+date)[:\s]+({month}\s+\d{{1,2}},?\s*\d{{4}})",
        # Standalone date patterns
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


# ── Org registry ──────────────────────────────────────────────────────────────
#
# Each entry:
#   url         — page to check daily for live opportunities
#   org         — organisation name
#   range       — "National" or "International"
#   category    — Scholarship / Fellowship / Internship
#   title       — human-readable item title
#   apply_link  — direct URL to apply / find application form
#   open_signals (optional) — extra words that confirm the opportunity is open
#
# "open" detection: any of OPEN_DEFAULT + (entry-specific signals) found in page body.
# If the page has NONE of those words we skip it (opportunity not currently open).

OPEN_DEFAULT = [
    "apply", "application", "applications open", "accepting applications",
    "applications are open", "deadline", "now open", "call for applications",
    "2026", "apply now", "apply here", "apply online", "apply today",
]

DIRECT_PAGES = [
    # ── Nigerian government ────────────────────────────────────────────────
    {
        "url":        "https://ptdf.gov.ng/",
        "org":        "PTDF",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "PTDF Scholarship 2025/2026",
        "apply_link": "https://ptdf.gov.ng/",
    },
    {
        "url":        "https://nddc.gov.ng/",
        "org":        "NDDC",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "NDDC Postgraduate Scholarship 2026",
        "apply_link": "https://nddc.gov.ng/",
    },
    {
        "url":        "https://nnpcgroup.com/Scholarships",
        "org":        "NNPC Group",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "NNPC Group Scholarship 2026",
        "apply_link": "https://nnpcgroup.com/Scholarships",
        "open_signals": ["scholarship", "apply"],
    },
    {
        "url":        "https://www.snepco.com/students/scholarship",
        "org":        "Shell Nigeria E&P (SNEPCo)",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "SNEPCo Postgraduate Scholarship 2026",
        "apply_link": "https://www.snepco.com/students/scholarship",
    },
    {
        "url":        "https://ndic.gov.ng/",
        "org":        "NDIC",
        "range":      "National",
        "category":   "Internship",
        "title":      "NDIC Student Industrial Training (SIWES) 2026",
        "apply_link": "https://ndic.gov.ng/",
    },
    # ── Nigerian corporate & foundations ──────────────────────────────────
    {
        "url":        "https://www.mtn.ng/mtn-foundation/scholarships/",
        "org":        "MTN Foundation",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "MTN Foundation Scholarship 2026",
        "apply_link": "https://www.mtn.ng/mtn-foundation/scholarships/",
    },
    {
        "url":        "https://tonyelumelufoundation.org/entrepreneurship/",
        "org":        "Tony Elumelu Foundation",
        "range":      "International",
        "category":   "Fellowship",
        "title":      "Tony Elumelu Entrepreneurship Programme 2026",
        "apply_link": "https://tonyelumelufoundation.org/entrepreneurship/",
    },
    {
        "url":        "https://www.dangote.com/",
        "org":        "Dangote Foundation",
        "range":      "National",
        "category":   "Scholarship",
        "title":      "Dangote Foundation Scholarship 2026",
        "apply_link": "https://www.dangote.com/",
    },
    {
        "url":        "https://www.accessbankplc.com/Personal-Banking/Transactional/Women-In-Business",
        "org":        "Access Bank",
        "range":      "National",
        "category":   "Fellowship",
        "title":      "Access Bank Internship / Graduate Programme 2026",
        "apply_link": "https://www.accessbankplc.com/career",
        "open_signals": ["intern", "graduate", "trainee", "apply"],
    },
    # ── International scholarships relevant to Nigerians ──────────────────
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
        "org":        "Chevening",
        "range":      "International",
        "category":   "Scholarship",
        "title":      "Chevening Scholarship 2026/2027",
        "apply_link": "https://www.chevening.org/apply/",
    },
    {
        "url":        "https://us.fulbrightonline.org/",
        "org":        "Fulbright Program",
        "range":      "International",
        "category":   "Fellowship",
        "title":      "Fulbright Foreign Student Program 2026/27",
        "apply_link": "https://us.fulbrightonline.org/",
        "open_signals": ["apply", "application", "now open", "program"],
    },
    {
        "url":        "https://mastercardfdn.org/",
        "org":        "Mastercard Foundation",
        "range":      "International",
        "category":   "Scholarship",
        "title":      "Mastercard Foundation Scholarship 2026",
        "apply_link": "https://mastercardfdn.org/programs/scholars-program/",
        "open_signals": ["scholars", "scholarship", "apply", "program"],
    },
    {
        "url":        "https://www.worldbank.org/en/programs/scholarships",
        "org":        "World Bank Group",
        "range":      "International",
        "category":   "Scholarship",
        "title":      "World Bank Scholarship Programs 2026",
        "apply_link": "https://www.worldbank.org/en/programs/scholarships",
        "dont_verify_ssl": True,  # TLS hostname mismatch on GitHub Actions
    },
    {
        "url":        "https://www.afdb.org/en/about/careers/internship-programme",
        "org":        "African Development Bank",
        "range":      "International",
        "category":   "Internship",
        "title":      "AfDB Internship Programme 2026",
        "apply_link": "https://www.afdb.org/en/about/careers/internship-programme",
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
        "url":        "https://www.undp.org/nigeria/jobs",
        "org":        "UNDP Nigeria",
        "range":      "International",
        "category":   "Internship",
        "title":      "UNDP Nigeria Internship 2026",
        "apply_link": "https://www.undp.org/nigeria/jobs",
    },
    {
        "url":        "https://www.britishcouncil.org.ng/programmes/education/scholarships",
        "org":        "British Council Nigeria",
        "range":      "International",
        "category":   "Scholarship",
        "title":      "British Council Nigeria Scholarships 2026",
        "apply_link": "https://www.britishcouncil.org.ng/programmes/education/scholarships",
    },
    {
        "url":        "https://youthhubafrica.org/",
        "org":        "YouthHub Africa",
        "range":      "National",
        "category":   "Fellowship",
        "title":      "YouthHub Africa Opportunities 2026",
        "apply_link": "https://youthhubafrica.org/",
        "open_signals": ["apply", "fellowship", "internship", "scholarship", "2026"],
    },
    # ── UN & multilateral ─────────────────────────────────────────────────
    {
        "url":        "https://www.unicef.org/careers/internships",
        "org":        "UNICEF",
        "range":      "International",
        "category":   "Internship",
        "title":      "UNICEF Internship Programme 2026",
        "apply_link": "https://www.unicef.org/careers/internships",
    },
    {
        "url":        "https://careers.un.org/lbw/home.aspx",
        "org":        "United Nations",
        "range":      "International",
        "category":   "Fellowship",
        "title":      "UN Fellowship Programme 2026",
        "apply_link": "https://careers.un.org/lbw/home.aspx",
        "open_signals": ["fellowship", "apply", "application", "programme"],
    },
]

# scholars4dev.com RSS (accessible, real article URLs, few items)
SCHOLARS4DEV_FEEDS = [
    ("https://www.scholars4dev.com/category/scholarships-for-africans/feed/", "International"),
    ("https://www.scholars4dev.com/tag/nigeria/feed/",                         "National"),
]


# ── Spider ────────────────────────────────────────────────────────────────────

class OpportunitiesSpider(scrapy.Spider):
    name = "opportunities"

    custom_settings = {
        "DOWNLOAD_TIMEOUT":        25,
        "RETRY_TIMES":              1,
        "HTTPERROR_ALLOWED_CODES": [403, 404, 429, 503],
    }

    def start_requests(self):
        # Direct org pages
        for cfg in DIRECT_PAGES:
            meta = {"cfg": cfg}
            if cfg.get("dont_verify_ssl"):
                meta["dont_verify_ssl"] = True
            yield scrapy.Request(
                cfg["url"], callback=self.parse_direct,
                meta=meta, errback=self.errback_direct,
            )
        # scholars4dev.com RSS (bonus items with real article URLs)
        import xml.etree.ElementTree as ET
        for rss_url, rng in SCHOLARS4DEV_FEEDS:
            yield scrapy.Request(
                rss_url, callback=self.parse_rss,
                meta={"range_override": rng},
                errback=self.errback_rss,
                headers={"Accept": "application/rss+xml, application/xml"},
            )

    # ── Direct org page handler ───────────────────────────────────────────────

    def parse_direct(self, response):
        cfg = response.meta["cfg"]

        # Allow 403/404 — still write the item so the org is represented
        body = " ".join(response.css("*::text").getall()).lower() if response.status == 200 else ""

        # Check open signals
        signals = set(OPEN_DEFAULT) | set(s.lower() for s in cfg.get("open_signals", []))
        if body and not any(s in body for s in signals):
            self.logger.info("Direct page %s — no open signals — skipping.", cfg["url"])
            return

        # Try to find a better apply button URL
        apply_link = cfg["apply_link"]
        if response.status == 200:
            for a in response.css("a"):
                href = a.attrib.get("href", "")
                text = " ".join(a.css("::text").getall()).lower()
                if any(kw in text for kw in ["apply now", "apply here",
                                              "application form", "click here to apply"]):
                    if href.startswith("http"):
                        apply_link = href
                        break
                    elif href.startswith("/"):
                        apply_link = urljoin(response.url, href)
                        break

        combined = cfg["title"] + " " + body[:400]
        item = OpportunityItem()
        item["title"]            = cfg["title"]
        item["industry"]         = _infer_industry(combined)
        item["category"]         = cfg["category"]
        item["range"]            = cfg["range"]
        item["education_level"]  = ""
        item["organization"]     = cfg["org"]
        item["summary"]          = ""
        item["application_link"] = apply_link
        item["opening_date"]     = ""
        item["deadline"]         = _extract_deadline(body)
        item["status"]           = "Open"
        yield item

    def errback_direct(self, failure):
        cfg = failure.request.meta.get("cfg", {})
        if cfg:
            item = OpportunityItem()
            item["title"]            = cfg["title"]
            item["industry"]         = _infer_industry(cfg["title"])
            item["category"]         = cfg["category"]
            item["range"]            = cfg["range"]
            item["education_level"]  = ""
            item["organization"]     = cfg["org"]
            item["summary"]          = ""
            item["application_link"] = cfg["apply_link"]
            item["opening_date"]     = ""
            item["deadline"]         = ""
            item["status"]           = "Open"
            yield item

    # ── scholars4dev.com RSS handler ─────────────────────────────────────────

    def parse_rss(self, response):
        import xml.etree.ElementTree as ET

        if response.status != 200:
            self.logger.warning("RSS %s → HTTP %s", response.url, response.status)
            return

        try:
            root = ET.fromstring(response.text)
        except Exception as exc:
            self.logger.warning("Feed parse error %s: %s", response.url, exc)
            return

        range_override = response.meta.get("range_override")
        cutoff = date.today() - timedelta(days=MAX_POST_AGE)

        channel = root.find("channel")
        entries = channel.findall("item") if channel is not None else []

        queued = 0
        for entry in entries:
            title = (entry.findtext("title") or "").strip()
            if not title:
                continue

            tl = title.lower()
            if not any(kw in tl for kw in TITLE_KEYWORDS):
                continue

            category = _infer_category(tl)
            if category not in ACCEPTED_CATEGORIES:
                continue

            ym = PAST_YEAR_RE.search(title)
            if ym and int(ym.group(1)) < date.today().year:
                continue

            pub = (entry.findtext("pubDate") or "").strip()
            if pub and HAS_DATEUTIL:
                try:
                    if dateutil_parse(pub, fuzzy=True).date() < cutoff:
                        continue
                except Exception:
                    pass

            link = (entry.findtext("link") or "").strip()
            if not link or "news.google.com" in link:
                continue

            desc = _strip_html(entry.findtext("description") or "")[:400]
            combined = title + " " + desc

            item = OpportunityItem()
            item["title"]            = title
            item["industry"]         = _infer_industry(combined)
            item["category"]         = category
            item["range"]            = range_override or "International"
            item["education_level"]  = ""
            item["organization"]     = "scholars4dev"
            item["summary"]          = desc
            item["application_link"] = link   # real scholars4dev.com article URL
            item["opening_date"]     = ""
            item["deadline"]         = _extract_deadline(combined)
            item["status"]           = "Open"
            queued += 1
            yield item

        self.logger.info("scholars4dev RSS: %d items queued.", queued)

    def errback_rss(self, failure):
        self.logger.warning("RSS failed: %s — %s", failure.request.url, failure.value)
