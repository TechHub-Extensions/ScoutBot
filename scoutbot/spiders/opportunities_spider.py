"""
ScoutBot opportunities spider — v4 "real links"

Flow for Google News items:
  1. Fetch Google News RSS → get CBMi redirect URL + title/description
  2. Follow CBMi → lands on news.google.com/articles/... page (Google, no Cloudflare)
  3. Extract the actual source article URL from that page's HTML/meta tags
  4. Follow source article URL → extract "Apply Here" button link
     - If article 403s (Cloudflare): store source article URL — still the real page
       e.g. opportunitydesk.org/mtn-scholarship-2026/ instead of news.google.com/...
     - If article loads: extract the direct apply/register link from the org's site

Additional direct sources (no Cloudflare):
  - scholars4dev.com  (RSS, both RSS 2.0 and Atom handled)
  - Tony Elumelu Foundation  (direct HTML)
  - MTN Foundation            (direct HTML)
  - World Bank scholarships   (direct HTML)
  - African Union internships (direct HTML)
  - UNDP Nigeria              (direct HTML)

Only three categories: Scholarship, Fellowship, Internship.
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


# ── Constants ─────────────────────────────────────────────────────────────────

ACCEPTED_CATEGORIES = {"Scholarship", "Fellowship", "Internship"}

CATEGORY_MAP = [
    ("scholarship", "Scholarship"),
    ("bursary",     "Scholarship"),
    ("grant",       "Scholarship"),
    ("funded",      "Scholarship"),
    ("fellowship",  "Fellowship"),
    ("exchange",    "Fellowship"),
    ("residency",   "Fellowship"),
    ("leadership program", "Fellowship"),
    ("internship",  "Internship"),
    ("industrial training", "Internship"),
    ("graduate trainee",    "Internship"),
    ("graduate programme",  "Fellowship"),
    ("graduate program",    "Fellowship"),
    ("apprenticeship",      "Internship"),
]

TITLE_KEYWORDS = [
    "scholarship", "fellowship", "internship", "bursary",
    "funded", "exchange programme", "graduate trainee",
    "industrial training", "apprenticeship",
]

PAST_YEAR_RE = re.compile(r"\b(202[0-4])\b")
MAX_POST_AGE = 10  # days

NIGERIA_SIGNALS = [
    "nigeria", "nigerian", "nigerians", "lagos", "abuja", "kano",
    "ibadan", "enugu", "owerri", "for nigerians", "open to nigerians",
]
INTL_SIGNALS = [
    "international", "study abroad", "global", "worldwide", "overseas",
    "fulbright", "commonwealth", "world bank", "united nations", " un ",
    "african union", "africa", "daad", "erasmus", "chevening", "mastercard",
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

# ── Google News RSS feeds (Nigeria-focused searches) ─────────────────────────
# These return news.google.com/rss/articles/CBMi... links.
# The spider resolves them → real article URLs via parse_gnews_page.

GNEWS_RSS = [
    "https://news.google.com/rss/search?q=nigeria+scholarship+2026&hl=en-NG&gl=NG&ceid=NG:en",
    "https://news.google.com/rss/search?q=nigeria+fellowship+2026&hl=en-NG&gl=NG&ceid=NG:en",
    "https://news.google.com/rss/search?q=nigeria+internship+2026&hl=en-NG&gl=NG&ceid=NG:en",
    "https://news.google.com/rss/search?q=fully+funded+scholarship+Nigeria+2026&hl=en&gl=NG&ceid=NG:en",
    "https://news.google.com/rss/search?q=fellowship+Nigeria+2026&hl=en&gl=NG&ceid=NG:en",
    "https://news.google.com/rss/search?q=commonwealth+scholarship+Nigeria&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=mastercard+foundation+scholarship+Africa+2026&hl=en&gl=US&ceid=US:en",
]

# ── Direct org pages (no Cloudflare — scraped for open opportunities) ─────────

DIRECT_PAGES = [
    # Tony Elumelu Foundation — flagship African entrepreneurship fellowship
    {
        "url": "https://tefffoundation.org/entrepreneurship-programme/apply/",
        "org": "Tony Elumelu Foundation",
        "range": "National",
        "category": "Fellowship",
        "title_hint": "Tony Elumelu Entrepreneurship Programme",
        "apply_link": "https://tefffoundation.org/entrepreneurship-programme/apply/",
    },
    # MTN Foundation scholarships
    {
        "url": "https://mtnfoundation.org.ng/scholarships/",
        "org": "MTN Foundation",
        "range": "National",
        "category": "Scholarship",
        "title_hint": "MTN Foundation Scholarship",
        "apply_link": "https://mtnfoundation.org.ng/scholarships/",
    },
    # World Bank Scholarships
    {
        "url": "https://www.worldbank.org/en/programs/scholarships",
        "org": "World Bank",
        "range": "International",
        "category": "Scholarship",
        "title_hint": "World Bank Scholarship",
        "apply_link": "https://www.worldbank.org/en/programs/scholarships",
    },
    # African Union Commission — Internship Programme
    {
        "url": "https://au.int/en/internship",
        "org": "African Union",
        "range": "International",
        "category": "Internship",
        "title_hint": "African Union Internship Programme",
        "apply_link": "https://au.int/en/internship",
    },
    # UNDP Nigeria jobs/internships
    {
        "url": "https://www.undp.org/nigeria/jobs",
        "org": "UNDP Nigeria",
        "range": "International",
        "category": "Internship",
        "title_hint": "UNDP Nigeria Internship",
        "apply_link": "https://www.undp.org/nigeria/jobs",
    },
]

# scholars4dev.com — loads fine from GitHub Actions, no Cloudflare
SCHOLARS4DEV_FEEDS = [
    "https://www.scholars4dev.com/feed/",
    "https://www.scholars4dev.com/category/scholarships-for-africans/feed/",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_category(text: str):
    t = text.lower()
    for kw, cat in CATEGORY_MAP:
        if kw in t:
            return cat
    return None  # reject


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


def _extract_apply_link(response) -> str:
    """Extract the best available application link from an article page."""
    base = urlparse(response.url).netloc

    # 1. WordPress / Elementor button blocks — most reliably link to org sites
    for sel in [
        ".wp-block-button a::attr(href)",
        ".wp-block-button__link::attr(href)",
        ".elementor-button::attr(href)",
        ".et_pb_button::attr(href)",
        "a.button::attr(href)",
        "a.btn-primary::attr(href)",
    ]:
        for href in response.css(sel).getall():
            if _is_external(href, base):
                return href

    # 2. Links with apply/register/official text in article body
    APPLY_TEXTS = {
        "apply here", "apply now", "click here to apply", "apply online",
        "apply for this", "start application", "apply via",
        "register here", "register now", "official website",
        "application form", "application portal", "here to apply",
        "application link", "click to apply",
    }
    for a in response.css(".entry-content a, .post-content a, article a, .content a"):
        href = a.attrib.get("href", "")
        if not _is_external(href, base):
            continue
        text = " ".join(a.css("::text").getall()).lower().strip()
        if any(kw in text for kw in APPLY_TEXTS):
            return href

    # 3. External links with apply/careers/form in href
    for href in response.css(
        ".entry-content a::attr(href), .post-content a::attr(href), article a::attr(href)"
    ).getall():
        if not _is_external(href, base):
            continue
        if any(s in href.lower() for s in ["apply", "application", "careers", "vacancy", "register"]):
            return href

    return response.url  # fall back to aggregator article page


def _extract_real_url_from_gnews(response) -> str:
    """
    Extract the real article URL from a news.google.com/articles/... page.

    Google News article pages contain the real source URL in several places:
      - <c-wiz jsdata="..."> with encoded URL
      - <a href="..."> links in the article header pointing off-site
      - <meta property="og:url" content="..."> (sometimes)
      - Canonical link or JSON-LD

    We try all known patterns and return the first non-google.com URL found.
    """
    base = "news.google.com"

    # Pattern 1: og:url meta tag
    og_url = response.css('meta[property="og:url"]::attr(content)').get("")
    if og_url and "news.google.com" not in og_url and og_url.startswith("http"):
        return og_url

    # Pattern 2: canonical link
    canonical = response.css('link[rel="canonical"]::attr(href)').get("")
    if canonical and "news.google.com" not in canonical and canonical.startswith("http"):
        return canonical

    # Pattern 3: first external <a href> in the article header/body
    for a in response.css("article a, h3 a, h4 a, .article a, [data-n-tid] a"):
        href = a.attrib.get("href", "")
        if href.startswith("http") and "news.google.com" not in href:
            return href

    # Pattern 4: any external link on the page
    for href in response.css("a::attr(href)").getall():
        if href.startswith("http") and "news.google.com" not in href and "google.com" not in href:
            return href

    return ""  # could not extract


# ── Spider ────────────────────────────────────────────────────────────────────

class OpportunitiesSpider(scrapy.Spider):
    name = "opportunities"

    custom_settings = {
        "DOWNLOAD_TIMEOUT": 20,
        "RETRY_TIMES":       1,
        "HTTPERROR_ALLOWED_CODES": [403, 429, 503],
    }

    def start_requests(self):
        # 1. Google News RSS feeds
        for url in GNEWS_RSS:
            yield scrapy.Request(
                url, callback=self.parse_gnews_rss,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                errback=self.errback_generic,
            )

        # 2. scholars4dev.com RSS feeds (both RSS 2.0 and Atom handled)
        for url in SCHOLARS4DEV_FEEDS:
            yield scrapy.Request(
                url, callback=self.parse_rss_generic,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                meta={"range_override": "International", "trust_source": True},
                errback=self.errback_generic,
            )

        # 3. Direct org pages
        for page in DIRECT_PAGES:
            yield scrapy.Request(
                page["url"], callback=self.parse_direct_org,
                meta={"page_cfg": page},
                errback=self.errback_direct,
            )

    def errback_generic(self, failure):
        self.logger.warning("Request failed: %s — %s", failure.request.url, failure.value)

    def errback_direct(self, failure):
        """For direct org pages: yield item with the configured apply_link."""
        cfg = failure.request.meta.get("page_cfg", {})
        if cfg:
            self.logger.debug("Direct org page %s failed — using configured apply_link.", cfg["url"])
            yield self._make_direct_item(cfg, body="")

    # ── Google News RSS → Google News article page → real article URL ─────────

    def parse_gnews_rss(self, response):
        """Parse Google News RSS and queue each article for URL resolution."""
        import xml.etree.ElementTree as ET

        if response.status != 200:
            self.logger.warning("RSS %s → HTTP %s", response.url, response.status)
            return

        try:
            root = ET.fromstring(response.text)
        except Exception as exc:
            self.logger.warning("RSS parse error: %s", exc)
            return

        channel = root.find("channel")
        if channel is None:
            return

        cutoff  = date.today() - timedelta(days=MAX_POST_AGE)
        queued  = 0

        for entry in channel.findall("item"):
            title = (entry.findtext("title") or "").strip()
            # Strip " - Source Name" suffix Google News appends
            title = re.sub(r"\s*[-–—]\s*[A-Za-z0-9][A-Za-z0-9 .,'&]+$", "", title).strip()
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

            pub_date = entry.findtext("pubDate") or ""
            if pub_date and HAS_DATEUTIL:
                try:
                    if dateutil_parse(pub_date, fuzzy=True).date() < cutoff:
                        continue
                except Exception:
                    pass

            gnews_link = (entry.findtext("link") or "").strip()
            if not gnews_link:
                continue

            raw_desc = entry.findtext("description") or ""
            summary  = _strip_html(raw_desc)[:400]
            combined = title + " " + summary

            src_el = entry.find("source")
            org    = (src_el.text or "").strip() if src_el is not None else ""

            item = OpportunityItem()
            item["title"]            = title
            item["industry"]         = _infer_industry(combined)
            item["category"]         = category
            item["range"]            = _infer_range(combined)
            item["education_level"]  = ""
            item["organization"]     = org
            item["summary"]          = summary
            item["application_link"] = gnews_link  # placeholder
            item["opening_date"]     = ""
            item["deadline"]         = _extract_deadline(combined)
            item["status"]           = "Open"

            queued += 1
            # Step 2: follow the CBMi link to news.google.com/articles/... page
            yield scrapy.Request(
                gnews_link,
                callback=self.parse_gnews_page,
                errback=self.errback_article,
                headers={"Referer": "https://news.google.com/"},
                meta={"item": item},
            )

        self.logger.info("Google News RSS %.50s…: %d items queued.", response.url, queued)

    def parse_gnews_page(self, response):
        """
        We are now on news.google.com/articles/... or a redirect destination.
        Extract the real source article URL from this Google News page.
        """
        item = response.meta["item"]

        # If we were redirected to the actual article already (non-google.com)
        if "news.google.com" not in response.url:
            item["application_link"] = response.url
            yield scrapy.Request(
                response.url,
                callback=self.parse_article,
                errback=self.errback_article,
                headers={"Referer": "https://news.google.com/"},
                meta={"item": item},
            )
            return

        # Extract real article URL from the Google News article page HTML
        real_url = _extract_real_url_from_gnews(response)
        if real_url:
            item["application_link"] = real_url  # at minimum, store the real URL
            yield scrapy.Request(
                real_url,
                callback=self.parse_article,
                errback=self.errback_article,
                headers={"Referer": "https://news.google.com/"},
                meta={"item": item},
            )
        else:
            # Couldn't extract real URL — item still has CBMi link (last resort)
            self.logger.debug("Could not extract real URL from %s", response.url)
            yield item

    # ── scholars4dev.com RSS (RSS 2.0 + Atom) ────────────────────────────────

    def parse_rss_generic(self, response):
        """Parse RSS 2.0 or Atom feeds — handles both formats."""
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
        trust_source   = response.meta.get("trust_source", False)
        cutoff         = date.today() - timedelta(days=MAX_POST_AGE)
        ns             = {"atom": "http://www.w3.org/2005/Atom"}
        queued         = 0

        # Detect RSS 2.0 vs Atom
        channel = root.find("channel")
        if channel is not None:
            # RSS 2.0
            entries = channel.findall("item")
            def _title(e): return e.findtext("title") or ""
            def _link(e):  return e.findtext("link") or ""
            def _desc(e):  return e.findtext("description") or ""
            def _date(e):  return e.findtext("pubDate") or ""
        else:
            # Atom
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
            def _title(e): return (e.findtext("{http://www.w3.org/2005/Atom}title") or "")
            def _link(e):
                for lnk in e.findall("{http://www.w3.org/2005/Atom}link"):
                    if lnk.get("rel", "alternate") == "alternate":
                        return lnk.get("href", "")
                return ""
            def _desc(e): return (
                e.findtext("{http://www.w3.org/2005/Atom}summary") or
                e.findtext("{http://www.w3.org/2005/Atom}content") or ""
            )
            def _date(e): return e.findtext("{http://www.w3.org/2005/Atom}published") or ""

        for entry in entries:
            title = _title(entry).strip()
            if not title:
                continue

            title_lower = title.lower()

            # For trusted sources (scholars4dev), only require category match
            if trust_source:
                category = _infer_category(title_lower) or "Scholarship"
            else:
                if not any(kw in title_lower for kw in TITLE_KEYWORDS):
                    continue
                category = _infer_category(title_lower)
                if category not in ACCEPTED_CATEGORIES:
                    continue

            ym = PAST_YEAR_RE.search(title)
            if ym and int(ym.group(1)) < date.today().year:
                continue

            pub_date = _date(entry)
            if pub_date and HAS_DATEUTIL:
                try:
                    if dateutil_parse(pub_date, fuzzy=True).date() < cutoff:
                        continue
                except Exception:
                    pass

            link = _link(entry).strip()
            if not link or not link.startswith("http"):
                continue

            raw_desc = _desc(entry)
            summary  = _strip_html(raw_desc)[:400]
            combined = title + " " + summary

            item = OpportunityItem()
            item["title"]            = title
            item["industry"]         = _infer_industry(combined)
            item["category"]         = category
            item["range"]            = _infer_range(combined, range_override)
            item["education_level"]  = ""
            item["organization"]     = ""
            item["summary"]          = summary
            item["application_link"] = link
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

        self.logger.info("Feed %.55s…: %d items queued.", response.url, queued)

    # ── Article page — extract real apply link ────────────────────────────────

    def parse_article(self, response):
        item = response.meta["item"]

        if response.status in (403, 429, 503):
            # Cloudflare blocked — use the article URL we already have.
            # It's a real human-readable page (e.g. opportunitydesk.org/...),
            # not a news.google.com link.
            self.logger.debug("Article %s → %s — keeping article URL.", response.url, response.status)
            yield item
            return

        apply_link = _extract_apply_link(response)
        item["application_link"] = apply_link

        # Upgrade deadline from full article body if not yet found
        if not item.get("deadline"):
            body = " ".join(response.css(
                ".entry-content *::text, .post-content *::text, article *::text"
            ).getall())
            item["deadline"] = _extract_deadline(body)

        # Upgrade org name from apply link domain
        if not item.get("organization"):
            parsed = urlparse(apply_link)
            if parsed.netloc and parsed.netloc != urlparse(response.url).netloc:
                item["organization"] = parsed.netloc.replace("www.", "")

        yield item

    def errback_article(self, failure):
        item = failure.request.meta.get("item")
        if item:
            self.logger.debug("Article %s failed — keeping current link.", failure.request.url)
            yield item

    # ── Direct org pages ──────────────────────────────────────────────────────

    def parse_direct_org(self, response):
        cfg = response.meta["page_cfg"]
        if response.status in (403, 429, 503):
            yield self._make_direct_item(cfg, body="")
            return

        body = " ".join(response.css("*::text").getall())

        # Check if the page mentions applications are currently open
        open_signals = ["apply", "applications open", "accepting applications",
                        "deadline", "apply now", "apply here"]
        if not any(s in body.lower() for s in open_signals):
            self.logger.info("Direct page %s shows no open opportunity signals — skipping.", cfg["url"])
            return

        # Try to extract a more specific apply link from the page
        apply_link = cfg["apply_link"]
        for a in response.css("a"):
            href = a.attrib.get("href", "")
            text = " ".join(a.css("::text").getall()).lower()
            if any(kw in text for kw in ["apply now", "apply here", "application form", "apply online"]):
                if href.startswith("http"):
                    apply_link = href
                    break
                elif href.startswith("/"):
                    apply_link = urljoin(response.url, href)
                    break

        yield self._make_direct_item(cfg, body=body[:400], apply_link=apply_link)

    def _make_direct_item(self, cfg, body="", apply_link=None):
        combined = cfg.get("title_hint", "") + " " + body
        item = OpportunityItem()
        item["title"]            = cfg.get("title_hint", "")
        item["industry"]         = _infer_industry(combined)
        item["category"]         = cfg.get("category", "Fellowship")
        item["range"]            = cfg.get("range", "National")
        item["education_level"]  = ""
        item["organization"]     = cfg.get("org", "")
        item["summary"]          = body[:300].strip()
        item["application_link"] = apply_link or cfg.get("apply_link", "")
        item["opening_date"]     = ""
        item["deadline"]         = _extract_deadline(body)
        item["status"]           = "Open"
        return item
