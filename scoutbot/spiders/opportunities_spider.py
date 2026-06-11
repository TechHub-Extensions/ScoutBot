"""
ScoutBot main spider — students only.

Scrapes scholarships, fellowships, internships, bootcamps, and
apprenticeships for Nigerian students. Startup/accelerator/VC content
is intentionally excluded.

Sources:
  - International aggregators (scholars4dev, opportunitydesk, etc.) via Google News RSS
  - Nigerian portals via Google News RSS
  - YouthHubAfrica Nigeria tag page (direct HTML scrape)

Quality rules:
  - application_link is the DIRECT apply URL on the org/company site,
    not the blog post or Google News redirect URL
  - Posts older than MAX_POST_AGE_DAYS days are skipped at parse time
  - Deadlines already past are dropped immediately
  - Items with no findable direct apply link are dropped (require_apply_link=True)
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
    "fulbright", "uk ", "usa", "europe", "canada", "australia",
    "china", "japan", "korea", "india", "asia", "singapore", "malaysia",
    "indonesia", "thailand", "taiwan", "hong kong", "vietnam", "bangladesh",
    "chinese government", "mext", "kgsp", "iccr", "csc scholarship",
    "adb ", "asian development",
]

# If the source URL itself contains "nigeria", force National regardless of content
NIGERIA_URL_MARKERS = ["nigeria", "/ng/", "naija"]

# Explicit Nigeria signals in opportunity body/title
NIGERIA_CONTENT_KEYWORDS = [
    "nigeria", "nigerian", "nigerians",
    "lagos", "abuja", "kano", "ibadan", "port harcourt",
    "enugu", "benin city", "kaduna", "owerri", "calabar",
    "open to nigerians", "for nigerians", "nigerian students",
    "nigerian citizens", "nigerian applicants", "nigerian youth",
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

# Only accept posts published within the last N days
MAX_POST_AGE_DAYS = 3

# Reddit subreddits (kept for future use)
REDDIT_SUBREDDITS = [
    "scholarships", "Internships", "gradadmissions",
    "studyabroad", "opportunities", "Nigeria", "Africa", "phd",
]

REDDIT_OPPORTUNITY_KEYWORDS = [
    "scholarship", "fellowship", "internship", "funded", "fully funded",
    "apply", "application", "deadline", "stipend", "bootcamp",
    "award", "opportunity", "programme", "program",
    "open to", "eligible", "phd", "masters", "msc", "mba", "undergraduate",
    "research", "exchange", "bursary", "training",
]

REDDIT_TITLE_KEYWORDS = [
    "scholarship", "fellowship", "internship", "grant", "funded", "funding",
    "bursary", "bootcamp", "accelerator", "exchange program", "training program",
    "award", "stipend", "phd program", "masters program", "postdoc",
    "fully funded", "open application", "call for applications",
    "now open", "applications open", "apply now",
]

REDDIT_ADVICE_WORDS = [
    "advice", "help", "tips", "question", "experience", "opinion",
    "lost", "confused", "struggling", "worried", "rant", "venting",
    "should i", "am i", "will i", "how do", "is it worth",
]

# ── Direct-apply link helpers ────────────────────────────────────────────────

KNOWN_APPLY_DOMAINS = {
    "forms.gle", "docs.google.com", "typeform.com", "submittable.com",
    "fluxx.io", "awardspring.com", "applyyourself.com", "embark.com",
    "smapply.io", "jotform.com", "wufoo.com", "academicworks.com",
    "commonapp.org", "ucas.com", "grantinterface.com", "grantrequest.com",
    "surveygizmo.com", "cognito.forms", "formassembly.com",
    "scholarshipamerica.org", "scholarships.com", "unigo.com",
}

SKIP_LINK_DOMAINS = {
    "reddit.com", "redd.it", "imgur.com", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "youtube.com", "tiktok.com",
    "t.co", "bit.ly", "ow.ly", "buff.ly",
}

APPLY_TEXT_KEYWORDS = [
    "apply now", "apply here", "apply online", "apply for this",
    "start application", "begin application", "application form",
    "official website", "official link", "official application",
    "click here to apply", "click to apply",
    "register now", "register here",
    "visit official", "visit website",
]

APPLY_HREF_PATTERNS = [
    "apply", "application", "admission", "admissions",
    "register", "enroll", "signup", "sign-up",
    "scholarship", "fellowship", "internship", "portal",
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


def infer_range(text, source_url=""):
    if any(m in source_url.lower() for m in NIGERIA_URL_MARKERS):
        return "National"
    text = text.lower()
    if any(kw in text for kw in RANGE_KEYWORDS_INTL):
        return "International"
    if any(kw in text for kw in NIGERIA_CONTENT_KEYWORDS):
        return "National"
    return "International"


def infer_edu(text):
    text = text.lower()
    for level, kws in EDU_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return level
    return "Any"


def extract_deadline(text):
    if re.search(r"\brolling\s+admissions?\b|\bapplications?\s+reviewed\s+monthly\b",
                 text, re.IGNORECASE):
        return "Rolling"

    month_expr = (
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
        r"|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?"
        r"|nov(?:ember)?|dec(?:ember)?)"
    )
    date_patterns = [
        r"\d{1,2}/\d{1,2}/\d{4}",
        rf"\d{{1,2}}(?:st|nd|rd|th)?\s+{month_expr}\s+\d{{4}}",
        rf"{month_expr}\s+\d{{1,2}},?\s*\d{{4}}",
        rf"{month_expr}\s+\d{{1,2}}",
    ]
    date_expr = "|".join(f"(?:{p})" for p in date_patterns)
    patterns = [
        rf"(?:applications?\s+close(?:s)?\s+on|submissions?\s+accepted\s+until|accepted\s+until)\s+({date_expr})",
        rf"(?:deadline|apply\s+by|closes?|closing\s+date)[:\s]+({date_expr})",
        rf"({date_expr})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return next(g for g in m.groups() if g is not None).strip()
    return ""


def is_expired(deadline_str, title=""):
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
    today = date.today()
    cutoff = today - timedelta(days=MAX_POST_AGE_DAYS)

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

    url_date = re.search(r"/(\d{4})/(\d{2})/", response.url)
    if url_date:
        try:
            y, m = int(url_date.group(1)), int(url_date.group(2))
            if date(y, m, 1) < cutoff.replace(day=1):
                return True
        except Exception:
            pass

    return False


def _score_link(href, link_text, blog_domain):
    if not href or not href.startswith("http"):
        return -1
    parsed = urlparse(href)
    domain = parsed.netloc.lower().replace("www.", "")

    if domain == blog_domain.lower().replace("www.", ""):
        return -1
    if any(skip in domain for skip in SKIP_LINK_DOMAINS):
        return -1

    path_q = (parsed.path + " " + (parsed.query or "")).lower()
    text_l = link_text.lower().strip()

    score = 0
    if any(ap in domain for ap in KNOWN_APPLY_DOMAINS):
        score += 100
    if any(kw in text_l for kw in APPLY_TEXT_KEYWORDS):
        score += 80
    elif "apply" in text_l or "official" in text_l or "register" in text_l:
        score += 50
    if any(p in path_q for p in APPLY_HREF_PATTERNS):
        score += 40
    if any(kw in domain for kw in ["scholarship", "fellow", "intern", "grant", "award"]):
        score += 20
    if score == 0:
        score = 1

    return score


def extract_direct_apply_link(response):
    """
    Walk every anchor on the page and return the URL most likely to be the
    organisation's own application page or form.

    Returns (link, found) where found=True means a real apply link was located;
    found=False means we could only fall back to the page URL itself.
    """
    blog_domain = urlparse(response.url).netloc

    scored = []
    for a in response.xpath("//a[@href]"):
        href = a.xpath("./@href").get("").strip()
        text = a.xpath("normalize-space(.)").get("").strip()
        s = _score_link(href, text, blog_domain)
        if s >= 0:
            scored.append((s, href))

    if scored:
        scored.sort(key=lambda x: -x[0])
        best_score, best_href = scored[0]
        if best_score > 1:
            return best_href, True

    return response.url, False


def _extract_apply_link_from_reddit_html(raw_html, post_url):
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', raw_html or "", re.IGNORECASE)
    scored = []
    for href in hrefs:
        if not href.startswith("http"):
            continue
        if href == post_url:
            continue
        parsed = urlparse(href)
        domain = parsed.netloc.lower().replace("www.", "")
        if any(skip in domain for skip in SKIP_LINK_DOMAINS):
            continue
        path_q = (parsed.path + " " + (parsed.query or "")).lower()
        score = 0
        if any(ap in domain for ap in KNOWN_APPLY_DOMAINS):
            score += 100
        if any(p in path_q for p in APPLY_HREF_PATTERNS):
            score += 50
        if any(kw in domain for kw in ["scholarship", "fellow", "intern", "grant", "award", "opportunity"]):
            score += 30
        if score > 0:
            scored.append((score, href))

    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def org_from_url(url):
    try:
        host = urlparse(url).netloc.replace("www.", "")
        name = host.split(".")[0].title()
        return name
    except Exception:
        return ""


class OpportunitiesSpider(scrapy.Spider):
    name = "opportunities"

    # HTML sources — scraped the normal way (article URL itself may be the apply page)
    start_urls = [
        "https://opportunities.youthhubafrica.org/tag/nigeria/",
    ]

    # Google News RSS — Nigeria-specific (routed to Nigeria tab)
    GOOGLE_NEWS_RSS_NIGERIA = [
        "https://news.google.com/rss/search?q=nigeria+scholarship+2026&hl=en-NG&gl=NG&ceid=NG:en",
        "https://news.google.com/rss/search?q=nigeria+fellowship+2026&hl=en-NG&gl=NG&ceid=NG:en",
        "https://news.google.com/rss/search?q=nigeria+internship+2026&hl=en-NG&gl=NG&ceid=NG:en",
        "https://news.google.com/rss/search?q=nigeria+bootcamp+OR+training+2026&hl=en-NG&gl=NG&ceid=NG:en",
    ]

    # Google News RSS — International (routed to International tab)
    GOOGLE_NEWS_RSS_INTL = [
        "https://news.google.com/rss/search?q=commonwealth+scholarship+2026+Nigeria&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=UK+scholarship+Nigeria+2026&hl=en&gl=GB&ceid=GB:en",
        "https://news.google.com/rss/search?q=international+fellowship+Africa+2026&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=world+bank+OR+UN+fellowship+Africa+2026&hl=en&gl=US&ceid=US:en",
    ]

    MAX_PAGES = 1

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)
        for url in self.GOOGLE_NEWS_RSS_NIGERIA:
            yield scrapy.Request(
                url, callback=self.parse_google_news_rss,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                meta={"forced_range": "National"},
            )
        for url in self.GOOGLE_NEWS_RSS_INTL:
            yield scrapy.Request(
                url, callback=self.parse_google_news_rss,
                headers={"Accept": "application/rss+xml, application/xml, text/xml"},
                meta={"forced_range": "International"},
            )

    def parse(self, response):
        """Parse a listing page and follow links to individual opportunity pages."""
        article_links = response.css(
            "article h2.entry-title a::attr(href), "
            "article h3.entry-title a::attr(href), "
            ".entry-title a::attr(href), "
            "h2.post-title a::attr(href), "
            "h3.post-title a::attr(href), "
            "h2.title a::attr(href), "
            "h3.title a::attr(href), "
            ".post-title a::attr(href), "
            ".post-header a::attr(href), "
            "article h2 a::attr(href), "
            "article h3 a::attr(href), "
            ".articles-list a.article-link::attr(href), "
            "main a[href*='/20']::attr(href)"
        ).getall()

        for link in article_links:
            link = link.strip()
            if not link or not link.startswith("http") or is_category_url(link):
                continue
            ym = PAST_YEAR_RE.search(link)
            if ym and int(ym.group(1)) < date.today().year:
                continue
            # HTML start_url articles: the page itself may be the apply page, so
            # we do NOT require an external apply link (require_apply_link=False)
            yield response.follow(
                link, self.parse_opportunity,
                meta={"listing_url": response.url, "require_apply_link": False},
            )

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
        """Parse an individual opportunity page and emit an item."""

        if is_old_post(response):
            return

        # Use RSS title as fallback if h1 not present on the article page
        rss_title = response.meta.get("rss_title", "")
        title = (
            response.css("h1.entry-title::text, h1.post-title::text, h1::text").get("").strip()
            or response.css("title::text").get("").strip()
            or rss_title
        )
        if not title:
            return

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

        category = infer_category(response.url, combined)
        if category in EXCLUDED_CATEGORIES:
            return

        # Extract the direct apply link.
        # For Google News RSS articles (require_apply_link=True): drop if none found.
        # For HTML start_url articles (require_apply_link=False): fall back to page URL.
        apply_link, found = extract_direct_apply_link(response)
        if not found and response.meta.get("require_apply_link", False):
            self.logger.debug(
                "parse_opportunity: no direct apply link on %s — dropped (require_apply_link)",
                response.url,
            )
            return

        # Respect forced_range set by the RSS parser; fall back to inference
        forced_range = response.meta.get("forced_range")
        if forced_range:
            range_val = forced_range
        else:
            range_val = infer_range(
                combined,
                source_url=response.meta.get("listing_url", response.url),
            )

        org = (
            response.css("meta[property='og:site_name']::attr(content)").get("")
            or org_from_url(response.url)
        )

        item = OpportunityItem()
        item["title"]            = title
        item["industry"]         = infer_industry(combined)
        item["category"]         = category
        item["range"]            = range_val
        item["education_level"]  = infer_edu(combined)
        item["organization"]     = org
        item["summary"]          = full_text[:400].strip()
        item["application_link"] = apply_link
        item["opening_date"]     = ""
        item["deadline"]         = deadline_str
        item["status"]           = "Open"

        yield item

    def parse_google_news_rss(self, response):
        """Parse Google News RSS feed.

        Pre-filters items by title keywords and post age. For each item that
        passes pre-filtering, follows the article URL so parse_opportunity can
        extract a real, direct application link from the article page itself.

        Items on Cloudflare-protected sites will fail to load and are dropped
        automatically. Items whose article pages contain no findable apply link
        are also dropped (require_apply_link=True).
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(response.text)
        except Exception as exc:
            self.logger.warning("Google News RSS parse failed — %s", exc)
            return

        channel = root.find("channel")
        if channel is None:
            return

        cutoff = date.today() - timedelta(days=MAX_POST_AGE_DAYS)
        queued = 0

        for entry in channel.findall("item"):
            title = (entry.findtext("title") or "").strip()
            if not title:
                continue

            # Drop past-year titles
            ym = PAST_YEAR_RE.search(title)
            if ym and int(ym.group(1)) < date.today().year:
                continue

            # Drop if too old
            pub_date = entry.findtext("pubDate") or ""
            if pub_date and HAS_DATEUTIL:
                try:
                    pub = dateutil_parse(pub_date, fuzzy=True).date()
                    if pub < cutoff:
                        continue
                except Exception:
                    pass

            # Title must look like a real opportunity listing
            title_lower = title.lower()
            if not any(kw in title_lower for kw in [
                "scholarship", "fellowship", "internship", "bootcamp",
                "training", "award", "programme", "program",
                "application", "apply", "funded", "grant", "bursary",
            ]):
                continue

            # Drop if deadline already passed (title-level check only)
            if is_expired("", title):
                continue

            link = entry.findtext("link") or ""
            if not link:
                continue

            # Follow the actual article URL so we can extract a direct apply link.
            # require_apply_link=True: drop if no external apply link found on the page.
            yield scrapy.Request(
                link,
                callback=self.parse_opportunity,
                errback=self.log_skipped,
                meta={
                    "forced_range": response.meta.get("forced_range", "National"),
                    "require_apply_link": True,
                    "rss_title": title,
                },
                dont_filter=False,
            )
            queued += 1

        self.logger.info(
            "Google News RSS (%s…): %d items queued for article fetch.",
            response.url[-50:], queued,
        )

    def log_skipped(self, failure):
        """Errback for RSS article requests — logs and silently drops."""
        self.logger.debug(
            "RSS article fetch failed (%s): %s — item dropped.",
            failure.value.__class__.__name__,
            failure.request.url[-80:],
        )

    def parse_reddit_rss(self, response):
        """Parse Reddit's public Atom RSS feed for a subreddit."""
        import xml.etree.ElementTree as ET

        sub = response.meta.get("subreddit", "reddit")
        try:
            root = ET.fromstring(response.text)
        except Exception as exc:
            self.logger.warning("Reddit r/%s: RSS parse failed — %s", sub, exc)
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

            title_lower = title.lower()
            if not any(kw in title_lower for kw in REDDIT_TITLE_KEYWORDS):
                continue
            if any(w in title_lower for w in REDDIT_ADVICE_WORDS):
                continue

            combined = (title + " " + body).lower()
            if not any(kw in combined for kw in REDDIT_OPPORTUNITY_KEYWORDS):
                continue

            deadline_str = extract_deadline(title + " " + body)
            if is_expired(deadline_str, title):
                continue

            category = infer_category(post_url, combined)
            if category in EXCLUDED_CATEGORIES:
                continue

            apply_link = _extract_apply_link_from_reddit_html(raw, post_url)
            if not apply_link:
                continue

            item = OpportunityItem()
            item["title"]            = title
            item["industry"]         = infer_industry(combined)
            item["category"]         = category
            item["range"]            = infer_range(combined, source_url=response.meta.get("listing_url", response.url))
            item["education_level"]  = infer_edu(combined)
            item["organization"]     = f"Reddit r/{sub}"
            item["summary"]          = body[:400].strip() or title
            item["application_link"] = apply_link
            item["opening_date"]     = ""
            item["deadline"]         = deadline_str
            item["status"]           = "Open"

            kept += 1
            yield item

        self.logger.info("Reddit r/%s: %d kept from %d entries.", sub, kept, len(entries))
