"""
ScoutBot main spider.

Scrapes international and Nigeria-specific opportunity sites for:
  - Scholarships, Fellowships, Internships, Bootcamps, Apprenticeships,
    Conferences — in Engineering, Tech, Law, Finance, General, Medicine.
  - Startup funding — Grants, VC funding, Accelerators, Incubators, Pitch
    Competitions — for tech and general startups, national + international.
"""

import re
from datetime import datetime
from urllib.parse import urlparse

import scrapy

from scoutbot.items import OpportunityItem


INDUSTRY_KEYWORDS = {
    "Startup": ["startup", "start-up", "founder", "entrepreneur", "entrepreneurship",
                "early-stage", "pre-seed", "seed round", "series a", "incubator",
                "accelerator", "venture capital", "vc fund", "angel investor",
                "early stage", "scale-up", "scaleup", "innovation hub", "founders"],
    "Tech": ["tech", "software", "coding", "developer", "data", "ai", "digital",
             "fintech", "ict", "computer", "stem", "cyber", "programming",
             "machine learning", "saas", "deeptech", "deep tech", "web3", "blockchain"],
    "Engineering": ["engineer", "mechanical", "civil", "electrical", "petroleum",
                    "chemical", "structural", "architecture"],
    "Law": ["law", "legal", "justice", "llb", "llm", "barrister", "solicitor",
            "rights", "policy"],
    "Finance": ["finance", "fintech", "accounting", "economics", "business",
                "commerce", "banking", "investment", "microfinance"],
    "Medicine": ["medicine", "health", "medical", "nursing", "pharma",
                 "biology", "public health", "research", "clinical"],
}

# Order matters — more specific patterns are checked first.
CATEGORY_MAP = [
    ("venture capital", "VC Funding"),
    ("vc fund", "VC Funding"),
    ("vc funding", "VC Funding"),
    ("seed round", "VC Funding"),
    ("series a", "VC Funding"),
    ("series b", "VC Funding"),
    ("pre-seed", "VC Funding"),
    ("angel invest", "VC Funding"),
    ("equity investment", "VC Funding"),
    ("incubator", "Incubator"),
    ("accelerator", "Accelerator"),
    ("pitch competition", "Pitch Competition"),
    ("pitch contest", "Pitch Competition"),
    ("startup competition", "Pitch Competition"),
    ("startup challenge", "Pitch Competition"),
    ("hackathon", "Pitch Competition"),
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
    ("grant", "Grant"),
    ("funding", "Grant"),
    ("competition", "Competition"),
    ("award", "Award"),
    ("graduate programme", "Fellowship"),
    ("programme", "Fellowship"),
    ("program", "Fellowship"),
    ("training", "Internship"),
]

RANGE_KEYWORDS_INTL = [
    "international", "study abroad", "global", "worldwide", "overseas",
    "fulbright", "commonwealth", "uk ", "usa", "europe", "canada", "australia",
    "fully funded", "full scholarship", "global accelerator",
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


def infer_edu(text, industry):
    """
    Education level applies to scholarships, fellowships, internships.
    For Startup-industry opportunities the concept doesn't apply, so default to "Any".
    """
    text = text.lower()
    for level, kws in EDU_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return level
    if industry == "Startup":
        return "Any"
    return "Bachelor"


def extract_deadline(text):
    patterns = [
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


def org_from_url(url):
    try:
        host = urlparse(url).netloc.replace("www.", "")
        name = host.split(".")[0].title()
        return name
    except Exception:
        return ""


class OpportunitiesSpider(scrapy.Spider):
    name = "opportunities"

    # Listing pages to visit
    start_urls = [
        # ============================================================
        # SCHOLARSHIPS / FELLOWSHIPS / INTERNSHIPS — for students
        # ============================================================
        # International
        "https://www.scholars4dev.com/category/scholarships-for-africans/",
        "https://www.opportunitiesforafricans.com/category/scholarships/",
        "https://www.opportunitiesforafricans.com/category/fellowships/",
        "https://www.opportunitiesforafricans.com/category/internships/",
        "https://afterschoolafrica.com/scholarships/",
        "https://afterschoolafrica.com/fellowships/",
        "https://afterschoolafrica.com/internships/",
        "https://afterschoolafrica.com/competitions/",
        "https://opportunitydesk.org/category/scholarships/",
        "https://opportunitydesk.org/category/fellowships/",
        "https://opportunitydesk.org/category/internships/",
        # Nigerian portals
        "https://scholarshipregion.com/category/nigeria-scholarships/",
        "https://myschoolng.com/scholarships/",
        # Youth Hub Africa
        "https://opportunities.youthhubafrica.org/category/scholarships-opportunities/",
        "https://opportunities.youthhubafrica.org/category/fellowships/",
        "https://opportunities.youthhubafrica.org/category/internships/",

        # ============================================================
        # STARTUP FUNDING — Grants, VC, Accelerators, Incubators
        # for tech startups and general startups
        # ============================================================
        # Grants & funding for African startups
        "https://opportunitydesk.org/category/grants/",
        "https://opportunitydesk.org/category/awards/",
        "https://opportunitydesk.org/category/competitions/",
        "https://opportunitydesk.org/category/entrepreneurship/",
        "https://www.opportunitiesforafricans.com/category/grants/",
        "https://www.opportunitiesforafricans.com/category/competitions/",
        "https://www.opportunitiesforafricans.com/category/entrepreneurship/",
        "https://afterschoolafrica.com/grants/",
        "https://afterschoolafrica.com/business/",
        # Youth Hub Africa — entrepreneurship & grants
        "https://opportunities.youthhubafrica.org/category/grants-2/",
        "https://opportunities.youthhubafrica.org/category/competitions/",
    ]

    MAX_PAGES = 3

    def parse(self, response):
        """Parse a listing page and yield requests to individual opportunity pages."""

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
            if link and link.startswith("http") and not is_category_url(link):
                yield response.follow(link, self.parse_opportunity)

        # Pagination
        current_page = int(response.meta.get("page", 1))
        if current_page < self.MAX_PAGES:
            next_page = response.css(
                "a.next.page-numbers::attr(href), "
                "a[rel='next']::attr(href), "
                "a.next::attr(href)"
            ).get()
            if next_page:
                yield response.follow(
                    next_page,
                    self.parse,
                    meta={"page": current_page + 1},
                )

    def parse_opportunity(self, response):
        """Parse an individual opportunity page and create an OpportunityItem."""

        title = (
            response.css("h1.entry-title::text, h1.post-title::text, h1::text").get("").strip()
            or response.css("title::text").get("").strip()
        )

        if not title:
            return

        full_text = " ".join(response.css(
            "article p::text, .entry-content p::text, .post-content p::text"
        ).getall())
        combined = title + " " + full_text

        apply_link = (
            response.css("a[href*='apply']::attr(href), a[href*='application']::attr(href)").get("")
            or response.url
        )

        org = (
            response.css("meta[property='og:site_name']::attr(content)").get("")
            or org_from_url(response.url)
        )

        industry = infer_industry(combined)

        item = OpportunityItem()
        item["title"] = title
        item["industry"] = industry
        item["category"] = infer_category(response.url, combined)
        item["range"] = infer_range(combined)
        item["education_level"] = infer_edu(combined, industry)
        item["organization"] = org
        item["summary"] = full_text[:400].strip()
        item["application_link"] = response.url
        item["opening_date"] = ""
        item["deadline"] = extract_deadline(combined)
        item["status"] = "Open"

        yield item
