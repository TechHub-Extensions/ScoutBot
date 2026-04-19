"""
Main ScoutBot spider.
Scrapes international and Nigeria-specific opportunity sites for:
  - Scholarships, Fellowships, Internships, Bootcamps, Apprenticeships,
    Conferences — in Engineering, Tech, Law, Finance, General, Medicine fields.
"""

import re
from datetime import datetime
from urllib.parse import urlparse

import scrapy

from scoutbot.items import OpportunityItem


INDUSTRY_KEYWORDS = {
    "Tech": ["tech", "software", "coding", "developer", "data", "ai", "digital", "fintech", "ict", "engineering", "computer", "stem", "cyber"],
    "Engineering": ["engineer", "mechanical", "civil", "electrical", "petroleum", "chemical", "structural"],
    "Law": ["law", "legal", "justice", "llb", "llm", "barrister", "solicitor", "rights"],
    "Finance": ["finance", "fintech", "accounting", "economics", "business", "commerce", "banking", "investment"],
    "Medicine": ["medicine", "health", "medical", "nursing", "pharma", "biology", "public health", "research"],
}

CATEGORY_MAP = {
    "scholarship": "Scholarship",
    "fellowships": "Fellowship",
    "fellowship": "Fellowship",
    "internship": "Internship",
    "internships": "Internship",
    "bootcamp": "Bootcamp",
    "boot-camp": "Bootcamp",
    "accelerator": "Bootcamp",
    "apprentice": "Apprenticeship",
    "conference": "Conference",
    "summit": "Conference",
    "grant": "Grant",
    "competition": "Competition",
    "award": "Award",
    "programme": "Fellowship",
    "program": "Fellowship",
    "training": "Internship",
}

RANGE_KEYWORDS_INTL = ["international", "study abroad", "global", "worldwide", "overseas", "fulbright", "commonwealth", "uk ", "usa", "europe", "canada", "australia"]
EDU_KEYWORDS = {
    "PhD": ["phd", "doctorate", "doctoral", "post-doctoral", "postdoctoral"],
    "Masters": ["masters", "master's", "msc", "mba", "postgraduate", "post-graduate", "graduate"],
    "Bachelor": ["bachelor", "undergraduate", "bsc", "beng", "llb", "first degree"],
    "HND/OND": ["hnd", "ond", "polytechnic"],
    "Any": ["any level", "all levels"],
}


def infer_industry(text):
    text = text.lower()
    for industry, kws in INDUSTRY_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return industry
    return "General"


def infer_category(url, text):
    combined = (url + " " + text).lower()
    for kw, cat in CATEGORY_MAP.items():
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

    start_urls = [
        # --- International scholarships / fellowships ---
        "https://www.scholars4dev.com/category/scholarships-for-africans/",
        "https://www.opportunitiesforafricans.com/category/scholarships/",
        "https://www.opportunitiesforafricans.com/category/fellowships/",
        "https://www.opportunitiesforafricans.com/category/internships/",
        "https://www.opportunitiesforafricans.com/",
        "https://afterschoolafrica.com/scholarships/",
        "https://afterschoolafrica.com/fellowships/",
        "https://afterschoolafrica.com/internships/",
        "https://afterschoolafrica.com/competitions/",
        "https://opportunitydesk.org/category/scholarships/",
        "https://opportunitydesk.org/category/fellowships/",
        "https://opportunitydesk.org/category/internships/",
        # --- Nigerian national portals ---
        "https://scholarshipregion.com/category/nigeria-scholarships/",
        "https://www.scholarshipair.com/",
        "https://myschoolng.com/scholarships/",
        # --- Bootcamps & tech programmes ---
        "https://www.opportunitiesforafricans.com/category/competitions/",
        # --- Youth Hub Africa ---
        "https://opportunities.youthhubafrica.org/category/scholarships-opportunities/",
        "https://opportunities.youthhubafrica.org/category/fellowships/",
        "https://opportunities.youthhubafrica.org/category/internships/",
    ]

    MAX_PAGES = 3  # limit pagination depth per spider run

    def parse(self, response):
        url = response.url

        # Generic article/post extractor — works across WordPress sites
        articles = response.css(
            "article, .post, .entry, div.item, div.col-md-4, li.clearfix"
        )

        if not articles:
            # Fallback: any heading with a link
            articles = response.css("h2, h3")

        for article in articles:
            title = (
                article.css("h2 a::text, h3 a::text, .entry-title a::text, h2::text, h3::text").get("").strip()
            )
            link = article.css(
                "h2 a::attr(href), h3 a::attr(href), .entry-title a::attr(href), a::attr(href)"
            ).get("").strip()

            if not title or not link or not link.startswith("http"):
                continue

            summary_parts = article.css(
                ".entry-summary p::text, .entry-content p::text, p::text, .excerpt::text"
            ).getall()
            summary = " ".join(s.strip() for s in summary_parts if s.strip())[:400]

            combined_text = title + " " + summary

            item = OpportunityItem()
            item["title"] = title
            item["industry"] = infer_industry(combined_text)
            item["category"] = infer_category(link + url, combined_text)
            item["range"] = infer_range(combined_text)
            item["education_level"] = infer_edu(combined_text)
            item["organization"] = org_from_url(link)
            item["summary"] = summary + ("Read more" if summary else "")
            item["application_link"] = link
            item["opening_date"] = ""
            item["deadline"] = extract_deadline(combined_text)
            item["status"] = "Open"

            yield item

        # Pagination — follow up to MAX_PAGES
        current_page = int(response.meta.get("page", 1))
        if current_page < self.MAX_PAGES:
            next_page = response.css(
                "a.next.page-numbers::attr(href), a[rel='next']::attr(href), "
                "a.next::attr(href), .pagination a:last-child::attr(href)"
            ).get()
            if next_page:
                yield response.follow(
                    next_page,
                    self.parse,
                    meta={"page": current_page + 1},
                )
