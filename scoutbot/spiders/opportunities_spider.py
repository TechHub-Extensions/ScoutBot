"""
ScoutBot main spider — students only.

Scrapes scholarships, fellowships, internships, bootcamps, and
apprenticeships for Nigerian students. Startup/accelerator/VC content
is intentionally excluded.

Sources:
  - International aggregators (scholars4dev, opportunitydesk, etc.)
  - Nigerian portals (scholarshipregion, myschoolng)
  - Asia-specific scholarship pages
  - Reddit RSS feeds (scholarships, internships, gradadmissions, etc.)

Quality rules:
  - application_link is the DIRECT apply URL on the org/company site,
    not the blog post URL
  - Posts older than 30 days are skipped at parse time
  - Deadlines already past are dropped immediately
  - Past-year titles are dropped at the URL-scan stage
"""

import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

import scrapy

from scoutbot.items import OpportunityItem

try:
    from dateutil.parser import parse as dateutil_parse
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


INDUSTRY_KEYWORDS = {
    "Tech": ["tech", "software", "coding", "developer", "data", "ai", "digital",
             "fintech", "ict", "computer", "stem", "cyber", "programming",
             "machine learning", "saas", "deeptech", "deep tech", "web3", "blockchain"],
    "Engineering": ["engineer", "mechanical", "civil", "electrical", "petroleum",
                    "chemical", "structural", "architecture"],
    "Law": ["law", "legal", "justice", "llb", "llm", "barrister", "solicitor",
            "rights", "policy"],
    "Finance": ["finance", "accounting", "economics", "business",
                "commerce", "banking", "investment", "microfinance"],
    "Medicine": ["medicine", "health", "medical", "nursing", "pharma",
                 "biology", "public health", "research", "clinical"],
}

# Student-focused categories only — no startup/VC/accelerator content
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

# Categories that are startup/funding — items in these categories are dropped
EXCLUDED_CATEGORIES = {
    "VC Funding", "Incubator", "Accelerator", "Pitch Competition", "Grant",
}

RANGE_KEYWORDS_INTL = [
    "international", "study abroad", "global", "worldwide", "overseas",
    "fulbright", "commonwealth", "uk ", "usa", "europe", "canada", "australia",
    "fully funded", "full scholarship",
    "china", "japan", "korea", "india", "asia", "singapore", "malaysia",
    "indonesia", "thailand", "taiwan", "hong kong", "vietnam", "bangladesh",
    "chinese government", "mext", "kgsp", "iccr", "csc scholarship",
    "adb ", "asian development",
]

EDU_KEYWORDS = {
    "PhD": ["phd", "doctorate", "doctoral", "post-doctoral", "postdoctoral"],
    "Masters": ["masters", "master's", "msc", "mba", "postgraduate",
                "post-graduate", "graduate"],
    "HND/OND": ["hnd", "ond", "polytechnic", "national diploma"],
    "Bachelor": ["bachelor", "undergraduate", "bsc", "beng", "llb", "first degree"],
    "Any": ["any level", "all levels", "all applicants", "any background", "open to all"],
}

# URL patterns that indicate a listing/category page rather than an individual opportunity
CATEGORY_URL_PATTERNS = [
    "/category/", "/tag/", "/page/", "?page=", "#", "/author/",
    "facebook.com/groups", "linkedin.com/company", "twitter.com",
]

PAST_YEAR_RE = re.compile(r"\b(202[0-4])\b")

# Maximum age of a scraped post before we skip it (days) — 3-week hard limit
MAX_POST_AGE_DAYS = 21

# Reddit subreddits (student-focused only)
REDDIT_SUBREDDITS = [
    "scholarships",
    "Internships",
    "gradadmissions",
    "studyabroad",
    "opportunities",
    "Nigeria",
    "Africa",
    "phd",
]

REDDIT_OPPORTUNITY_KEYWORDS = [
    "scholarship", "fellowship", "internship", "funded", "fully funded",
    "apply", "application", "deadline", "stipend", "bootcamp",
    "award", "opportunity", "programme", "program",
    "open to", "eligible", "phd", "masters", "msc", "mba", "undergraduate",
    "research", "exchange", "bursary", "training",
]


def is_category_url(url):
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in CATEGORY_URL_PATTERNS)


def infer_industry(text):
    text = text.lower()
    for industry, kws in INDUSTRY_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return industry
    return "General"


def infer_category(url, text):
    combined = (url + " " + text).lower()
    for kw, cat in CATEGORY_MAP:
        if kw in combined:
            return cat
    return "Opportunity"


def infer_range(text):
    text = text.lower()
    if any(kw in text for kw in RANGE_KEYWORDS_INTL):
        return "International"
    return "National"


def infer_edu(text):
    text = text.lower()
    for level, kws in EDU_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return level
    return "Any"


def extract_deadline(text):
    patterns = [
        r"applications?\s+close\s+on\s+(\d{1,2}/\d{1,2}/\d{4})",
        r"deadline[:\s]+(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})",
        r"submissions?\s+accepted\s+until\s+([A-Za-z]+\s+\d{1,2})",
        r"(rolling admissions?)",
        r"deadline[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"apply by[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"closes?[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"closing date[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"(\d{1,2} [A-Za-z]+ \d{4})",
        r"([A-Za-z]+ \d{1,2},?\s*\d{4})",
    ]

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    return ""


def is_expired(deadline_str, title=""):
    """Return True if the opportunity is clearly in the past."""
    today = date.today()
    if title:
        for m in PAST_YEAR_RE.finditer(title):
            if int(m.group(1)) < today.year:
                return True
    if not deadline_str or not HAS_DATEUTIL:
        return False
    try:
        d = dateutil_parse(deadline_str, fuzzy=True, dayfirst=False).date()
        return d < today
    except Exception:
        return False


def is_old_post(response):
    """Return True if the page is clearly more than MAX_POST_AGE_DAYS old."""
    today = date.today()
    cutoff = today - timedelta(days=MAX_POST_AGE_DAYS)

    # 1. Check <time datetime="..."> tag
    pub_date_str = response.css(
        "time[datetime]::attr(datetime), "
        "meta[property='article:published_time']::attr(content)"
    ).get("")
    if pub_date_str and HAS_DATEUTIL:
        try:
            pub = dateutil_parse(pub_date_str, fuzzy=True).date()
            if pub < cutoff:
                return True
        except Exception:
            pass

    # 2. Check URL date pattern — e.g. /2025/03/ or /2024/11/
    url_date = re.search(r"/(\d{4})/(\d{2})/", response.url)
    if url_date:
        try:
            y, m = int(url_date.group(1)), int(url_date.group(2))
            if date(y, m, 1) < cutoff.replace(day=1):
                return True
        except Exception:
            pass

    return False


def extract_direct_apply_link(response):
    """
    Find the best direct application URL on the page.
    Prefers links that go to a DIFFERENT domain from the blog/aggregator
    (i.e., the actual company or program application page).
    Falls back to any apply-looking link, then to the page URL itself.
    """
    blog_domain = urlparse(response.url).netloc

    # Selectors ordered by specificity
    candidates = response.css(
        "a[href*='apply']::attr(href), "
        "a[href*='application']::attr(href), "
        "a[href*='admission']::attr(href), "
        "a[href*='register']::attr(href), "
        "a[href*='enroll']::attr(href), "
        "a[href*='portal']::attr(href)"
    ).getall()

    # Filter to absolute HTTP URLs only
    abs_candidates = [l for l in candidates if l and l.startswith("http")]

    # Prefer external (non-blog) domain links — these are the actual org sites
    external = [l for l in abs_candidates if urlparse(l).netloc != blog_domain]
    if external:
        return external[0]

    # Fall back to any absolute apply link
    if abs_candidates:
        return abs_candidates[0]

    # Last resort: the page URL itself
    return response.url


def org_from_url(url):
    try:
        host = urlparse(url).netloc.replace("www.", "")
        name = host.split(".")[0].title()
        return name
    except Exception:
        return ""


class OpportunitiesSpider(scrapy.Spider):
    name = "opportunities"

    # Student-focused listing pages only — startup/funding URLs removed
    start_urls = [
        # ── International aggregators ──────────────────────────────────────
        "https://www.scholars4dev.com/category/scholarships-for-africans/",
        "https://www.opportunitiesforafricans.com/category/scholarships/",
        "https://www.opportunitiesforafricans.com/category/fellowships/",
        "https://www.opportunitiesforafricans.com/category/internships/",
        "https://afterschoolafrica.com/scholarships/",
        "https://afterschoolafrica.com/fellowships/",
        "https://afterschoolafrica.com/internships/",
        "https://opportunitydesk.org/category/scholarships/",
        "https://opportunitydesk.org/category/fellowships/",
        "https://opportunitydesk.org/category/internships/",
        # ── Nigerian portals ───────────────────────────────────────────────
        "https://scholarshipregion.com/category/nigeria-scholarships/",
        "https://myschoolng.com/scholarships/",
        # ── Youth Hub Africa ───────────────────────────────────────────────
        "https://opportunities.youthhubafrica.org/category/scholarships-opportunities/",
        "https://opportunities.youthhubafrica.org/category/fellowships/",
        "https://opportunities.youthhubafrica.org/category/internships/",
        # ── Asia-specific (open to Africans) ──────────────────────────────
        "https://www.scholars4dev.com/category/scholarships-in-asia/",
        "https://www.scholars4dev.com/category/scholarships-in-china/",
        "https://www.scholars4dev.com/category/scholarships-in-japan/",
        "https://www.scholars4dev.com/category/scholarships-in-south-korea/",
        "https://www.scholars4dev.com/category/scholarships-in-india/",
        "https://opportunitydesk.org/?s=china+scholarship+africa",
        "https://opportunitydesk.org/?s=japan+scholarship+africa",
        "https://opportunitydesk.org/?s=korea+scholarship+africa",
        "https://opportunitydesk.org/?s=asian+scholarship",
        "https://www.opportunitiesforafricans.com/?s=china",
        "https://www.opportunitiesforafricans.com/?s=japan",
        "https://www.opportunitiesforafricans.com/?s=korea",
        "https://www.opportunitiesforafricans.com/?s=india",
        "https://afterschoolafrica.com/?s=china+scholarship",
        "https://afterschoolafrica.com/?s=japan+scholarship",
        "https://afterschoolafrica.com/?s=korea+scholarship",
        "https://opportunitydesk.org/?s=asian+development+bank",
        "https://opportunities.youthhubafrica.org/?s=china",
        "https://opportunities.youthhubafrica.org/?s=japan",
        "https://opportunities.youthhubafrica.org/?s=korea",
    ]

    MAX_PAGES = 2  # Reduced from 3 to keep results recent

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

        for sub in REDDIT_SUBREDDITS:
            url = f"https://www.reddit.com/r/{sub}/new/.rss?limit=25"
            yield scrapy.Request(
                url,
                callback=self.parse_reddit_rss,
                headers={
                    "Accept": "application/rss+xml, application/xml, text/xml",
                    "User-Agent": "python:scoutbot.opportunities-aggregator:v1.0 (by /u/scoutbot_ng)",
                },
                meta={"subreddit": sub},
            )

    def parse(self, response):
        """Parse a listing page and follow links to individual opportunity pages."""
        article_links = response.css(
            "article h2.entry-title a::attr(href), "
            "article h3.entry-title a::attr(href), "
            ".entry-title a::attr(href), "
            "h2.post-title a::attr(href), "
            "h2.title a::attr(href), "
            ".post-title a::attr(href), "
            "article h2 a::attr(href), "
            "article h3 a::attr(href)"
        ).getall()

        for link in article_links:
            link = link.strip()
            if not link or not link.startswith("http") or is_category_url(link):
                continue
            # Pre-filter: skip if the URL contains a past year
            ym = PAST_YEAR_RE.search(link)
            if ym and int(ym.group(1)) < date.today().year:
                continue
            yield response.follow(link, self.parse_opportunity)

        # Pagination — not for search URLs, and capped at MAX_PAGES
        if "?s=" not in response.url:
            current_page = int(response.meta.get("page", 1))
            if current_page < self.MAX_PAGES:
                next_page = response.css(
                    "a.next.page-numbers::attr(href), "
                    "a[rel='next']::attr(href), "
                    "a.next::attr(href)"
                ).get()
                if next_page:
                    yield response.follow(
                        next_page, self.parse,
                        meta={"page": current_page + 1},
                    )

    def parse_opportunity(self, response):
        """Parse an individual opportunity page."""

        # Skip old pages immediately
        if is_old_post(response):
            return

        title = (
            response.css("h1.entry-title::text, h1.post-title::text, h1::text").get("").strip()
            or response.css("title::text").get("").strip()
        )
        if not title:
            return

        # Drop past-year titles
        ym = PAST_YEAR_RE.search(title)
        if ym and int(ym.group(1)) < date.today().year:
            return

        full_text = " ".join(response.css(
            "article p::text, .entry-content p::text, .post-content p::text"
        ).getall())
        combined = title + " " + full_text

        deadline_str = extract_deadline(combined)
        if is_expired(deadline_str, title):
            return

        # Infer category and drop startup/funding content
        category = infer_category(response.url, combined)
        if category in EXCLUDED_CATEGORIES:
            return

        # ── KEY FIX: use the direct apply URL, not the blog post URL ──────
        apply_link = extract_direct_apply_link(response)

        org = (
            response.css("meta[property='og:site_name']::attr(content)").get("")
            or org_from_url(response.url)
        )

        industry = infer_industry(combined)

        item = OpportunityItem()
        item["title"]            = title
        item["industry"]         = industry
        item["category"]         = category
        item["range"]            = infer_range(combined)
        item["education_level"]  = infer_edu(combined)
        item["organization"]     = org
        item["summary"]          = full_text[:400].strip()
        item["application_link"] = apply_link
        item["opening_date"]     = ""
        item["deadline"]         = deadline_str
        item["status"]           = "Open"

        yield item

    def parse_reddit_rss(self, response):
        """Parse Reddit's public Atom RSS feed for a subreddit."""
        import xml.etree.ElementTree as ET

        sub = response.meta.get("subreddit", "reddit")
        try:
            root = ET.fromstring(response.text)
        except Exception as exc:
            self.logger.warning(f"Reddit r/{sub}: RSS parse failed — {exc}")
            return

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        now_ts = datetime.now(tz=timezone.utc).timestamp()
        cutoff_ts = now_ts - (MAX_POST_AGE_DAYS * 86400)
        kept = 0

        for entry in entries:
            t_el = entry.find("atom:title", ns)
            title = (t_el.text or "").strip() if t_el is not None else ""
            if not title:
                continue

            ym = PAST_YEAR_RE.search(title)
            if ym and int(ym.group(1)) < date.today().year:
                continue

            link_el = entry.find("atom:link", ns)
            post_url = link_el.get("href", "") if link_el is not None else ""

            upd_el = entry.find("atom:updated", ns)
            if upd_el is not None and upd_el.text:
                try:
                    ts = datetime.fromisoformat(
                        upd_el.text.replace("Z", "+00:00")
                    ).timestamp()
                    if ts < cutoff_ts:
                        continue
                except Exception:
                    pass

            c_el = entry.find("atom:content", ns)
            raw = c_el.text or "" if c_el is not None else ""
            body = re.sub(r"<[^>]+>", " ", raw)
            body = re.sub(r"\s+", " ", body).strip()
            if body in ("[removed]", "[deleted]"):
                body = ""

            combined = (title + " " + body).lower()
            if not any(kw in combined for kw in REDDIT_OPPORTUNITY_KEYWORDS):
                continue

            deadline_str = extract_deadline(title + " " + body)
            if is_expired(deadline_str, title):
                continue

            category = infer_category(post_url, combined)
            if category in EXCLUDED_CATEGORIES:
                continue

            apply_link = post_url or f"https://www.reddit.com/r/{sub}/"
            industry = infer_industry(combined)

            item = OpportunityItem()
            item["title"]            = title
            item["industry"]         = industry
            item["category"]         = category
            item["range"]            = infer_range(combined)
            item["education_level"]  = infer_edu(combined)
            item["organization"]     = f"Reddit r/{sub}"
            item["summary"]          = body[:400].strip() or title
            item["application_link"] = apply_link
            item["opening_date"]     = ""
            item["deadline"]         = deadline_str
            item["status"]           = "Open"

            kept += 1
            yield item

        self.logger.info(f"Reddit r/{sub}: {kept} kept from {len(entries)} entries.")
