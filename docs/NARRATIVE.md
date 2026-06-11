# ScoutBot — Written Narrative for Hackathon Submission

**Submitted by:** Kamsi Richard Ivanna, TechHub Extensions  
**Category:** Education & Human Potential / Entrepreneurship & Job Creation  
**Word count:** ~850

---

## Rewriting the Discovery Pipeline for Nigerian Students

Every year, thousands of scholarships, fellowships, and internship programmes designed for Nigerian students go unclaimed — not because students are unqualified, but because the information never reaches them. Opportunities scatter across 30+ websites, WhatsApp group screenshots, and emails that never get forwarded. By the time a student hears about an opportunity, the deadline has passed. ScoutBot is the fix.

ScoutBot is an AI-native pipeline that runs every day, finds every new opportunity across both Nigerian and international sources, evaluates it for quality and relevance using Google Gemini AI, and delivers a curated weekly digest to 500+ Nigerian students every Sunday — free, automated, and independently operated on GitHub Actions with zero server cost.

---

## What AI Does Day to Day

ScoutBot's AI pipeline runs without human intervention. Every morning at 7:00 AM West Africa Time, GitHub Actions triggers a Scrapy spider that pulls from 8 Google News RSS feeds spanning both Nigeria-specific channels (scholarships, fellowships, internships, training programmes in Nigerian locale) and international channels (Commonwealth, UK, UN, World Bank, Africa fellowships).

Each item that survives the 3-day freshness window is handed to **Google Gemini 2.0 Flash**. Gemini does two things automatically:

1. **Scores each opportunity 1–10** for relevance to Nigerian students — evaluating whether the opportunity is genuinely open to Nigerians, currently accepting applications, and actually a student programme rather than a news article or event for professionals.
2. **Writes a 2-sentence blurb** that appears under each opportunity in the Sunday email — "Fully funded UK postgraduate study for Nigerian graduates in STEM fields — apply by July 31 via the NNPC portal."

Items scoring below 5 are silently dropped. Items already in the Google Sheet are pre-filtered before Gemini sees them, so the AI quota is never wasted on content already delivered. The result: only fresh, AI-verified, relevant opportunities enter the sheet — automatically, daily, with no human editorial review required.

AI executes three key decisions in ScoutBot's operations: (1) whether an opportunity meets the quality bar for Nigerian students; (2) what the student-facing summary of that opportunity says; and (3) whether to route the opportunity to the Nigeria tab or the International tab of the shared spreadsheet.

---

## What Humans Do

The founding team does what AI cannot:

- **Source selection and curation** — deciding which RSS feeds to monitor, based on lived knowledge of where legitimate Nigerian opportunities are actually posted and which sources are trustworthy vs. clickbait
- **Subscriber relationships** — responding to subscribers who reply to the digest, moderating the subscription form, and deciding when to send special announcements
- **System evolution** — tuning the Gemini scoring prompt, expanding to new source categories, and making architectural decisions about freshness windows and lifecycle management
- **Community building** — coordinating 6 open-source contributors across 4 countries who have collectively merged 50+ pull requests improving the scraping, email, and AI subsystems

The human-to-AI ratio in day-to-day operations is roughly 1 hour per week of human time (reviewing pull requests, monitoring weekly digest quality) versus 7 days per week of continuous AI-native execution.

---

## Economic Opportunity Created and Enabled

**For students:** 500+ Nigerian students receive a verified weekly digest of opportunities they would otherwise spend hours searching for. A student who finds a fully funded scholarship avoids ₦3,000,000–₦10,000,000 in education costs. A student placed in an internship gains work experience that directly increases their employment value and lifetime earning potential.

**For contributors:** ScoutBot is open source and has become a learning platform. Six developers have used the project to build portfolio-worthy skills in Python, Scrapy, AI API integration, email systems, and GitHub Actions — skills that translate directly to employment in Nigerian and international tech markets. The project's pull request history is a hiring signal: contributors can point to merged, production-running code as evidence of real engineering ability.

**For the Nigerian talent pipeline:** By reducing the information asymmetry that keeps most Nigerian students from applying for international programmes, ScoutBot increases the number of Nigerians who compete for — and win — global scholarships, fellowships, and internship placements. At scale, this directly increases Nigeria's share of international educational investment in African students.

---

## The Story of Building This Way

ScoutBot began as a manual process: Kamsi Richard Ivanna copying and pasting opportunity links into a Google Sheet every morning. It took two hours per day, missed most opportunities, and was unsustainable.

The AI layer changed the economics entirely. With Gemini scoring items, ScoutBot can evaluate hundreds of potential opportunities per day and filter down to only the ones worth delivering — without any human reading each one. The email digest that once took two hours to curate now writes itself.

The project was built with zero budget on entirely free infrastructure: GitHub Actions (free tier), Gemini API (free tier), Gmail SMTP (free), Google Sheets (free). That constraint forced every architectural decision toward efficiency — which is why deduplication runs before the AI call (no wasted quota), why the freshness window is 3 days (no stale content), and why the digest runs weekly rather than daily (subscribers actually read it instead of unsubscribing).

ScoutBot is a proof that AI-native operations at meaningful scale do not require a server, a SaaS budget, or a team of engineers. They require the right architecture, the right problem, and the discipline to let AI execute decisions while humans focus on what AI cannot yet do: judgment, relationships, and the lived experience of being a Nigerian student trying to find their way in the world.
