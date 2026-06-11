# ScoutBot — Volunteer Roles & Responsibilities

ScoutBot is a free, open-source tool built by Nigerian students for Nigerian students.
This document defines every volunteer role: what it involves, time commitment, required
skills, and step-by-step instructions for doing the work.

**Founder / Project Lead (not a volunteer role):** Kamsi Richard Ivanna retains final
decision authority, credential management, and the right to merge to `main`. All other
roles listed here are open to community volunteers.

---

## Role Overview

| Role | Time/week | Skills | Level |
|------|-----------|--------|-------|
| [1. Source Hunter](#1-source-hunter) | 1–3 hrs | Browser research | Beginner |
| [2. Source Monitor](#2-source-monitor) | 30 min | Browser + GitHub | Beginner |
| [3. Community Ambassador](#3-community-ambassador) | 1–2 hrs | Writing, social | Beginner |
| [4. Issue Triager](#4-issue-triager) | 30 min | Basic GitHub | Easy |
| [5. Documentation Writer](#5-documentation-writer) | 2–4 hrs | Writing + Markdown | Easy |
| [6. Data Curator](#6-data-curator) | 1–2 hrs | Google Sheets | Easy |
| [7. Email Template Designer](#7-email-template-designer) | 2–5 hrs | HTML + CSS | Intermediate |
| [8. PR Reviewer](#8-pr-reviewer) | 1–2 hrs | Python | Intermediate |
| [9. QA Tester](#9-qa-tester) | 2–4 hrs | Python, CLI | Intermediate |
| [10. Subscriber Support](#10-subscriber-support) | 30 min | Gmail | Beginner |

---

## 1. Source Hunter

**What this role does:**
Find new websites and RSS feeds that publish opportunities for Nigerian students —
scholarships, fellowships, internships, bootcamps. Every source you add can deliver
dozens of new opportunities per month to 500+ subscribers.

**Time:** 1–3 hours per week, flexible.
**Skills needed:** No coding. Just a browser and judgment.

### What makes a good source
- Posts opportunities regularly (at least monthly)
- Targets students specifically (not professionals or NGOs)
- Opportunities are open to Nigerians or Africans broadly
- Has an RSS feed OR appears consistently in Google News results
- Provides direct application links, not news articles

### Step-by-step

**Step 1 — Search Google News:**
Use queries like `scholarship 2026 Nigeria students`, `fellowship Africa 2026 apply`,
`internship Nigeria university 2026`. Note the domain names that appear consistently.

**Step 2 — Test for an RSS feed:**
Try adding `/feed`, `/rss`, or `/feed.xml` to the domain URL.
Or paste the URL into https://rss.app/rss-feed to auto-detect it.
Or use Google News RSS directly:
```
https://news.google.com/rss/search?q=scholarship+Nigeria+2026&hl=en-NG&gl=NG&ceid=NG:en
```

**Step 3 — Quality check the source manually:**
Visit the site and read 5 recent posts. Confirm:
- ✅ Posts have direct application URLs (not "contact us")
- ✅ At least 3 of the 5 most recent posts are still open (deadline not passed)
- ✅ Content is student-focused (scholarships, fellowships, internships, bootcamps)
- ❌ NOT Cloudflare-protected — to test: paste the URL in a fresh browser; if you see
  "Checking your browser…" it's blocked and will silently return 0 results on GitHub Actions

**Step 4 — Submit your finding:**
Open a GitHub Issue at:
`https://github.com/TechHub-Extensions/ScoutBot/issues/new?template=new_source.yml`
Fill in: source name, URL, RSS feed URL, category, screenshot of a recent post.
Label: `new-source`.

**Step 5 (optional) — Submit a PR directly:**
Fork the repo, open `scoutbot/spiders/opportunities_spider.py`, and add the RSS URL
to `GOOGLE_NEWS_RSS_NIGERIA` or `GOOGLE_NEWS_RSS_INTL`. Open a PR titled:
`feat: add [Source Name] as opportunity source`

### What NOT to submit
- Cloudflare-protected sites (silently return 0 results in production)
- Sites that repost from sources already in the spider
- Company job boards (ScoutBot is students-only)
- Sites requiring login to view listings

---

## 2. Source Monitor

**What this role does:**
Verify that ScoutBot's existing RSS feeds are still alive every week. A source can
die quietly — domain expired, feed URL changed — and the bot produces 0 results with
no visible error. Someone needs to catch this before it goes unnoticed for weeks.

**Time:** 30 minutes every Monday.
**Skills needed:** Browser + GitHub. No coding required.

### Step-by-step

**Step 1 — Find the feed URLs:**
Open `scoutbot/spiders/opportunities_spider.py` on GitHub:
`https://github.com/TechHub-Extensions/ScoutBot/blob/main/scoutbot/spiders/opportunities_spider.py`
Find `GOOGLE_NEWS_RSS_NIGERIA` and `GOOGLE_NEWS_RSS_INTL`. Copy each full URL.

**Step 2 — Test each URL in your browser:**
- XML file with `<item>` entries → ✅ healthy
- Error page, blank page, or "Checking your browser…" → ❌ dead
- XML loads but all items are older than 14 days → ⚠️ slow source (note it, not urgent)

**Step 3 — Check the Actions run history for patterns:**
Go to `https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/scoutbot.yml`
A feed that logs `0 kept` across 5+ consecutive daily runs is likely dead or throttled.

**Step 4 — Report:**
- All feeds healthy → add a comment on issue #50: "Source health check [date]: all OK"
- Dead source found → open a new issue:
  Title: `bug: [source name] feed dead or returning 0 results`
  Include: the URL, what you see when visiting it, how many consecutive days it showed 0.

---

## 3. Community Ambassador

**What this role does:**
Grow ScoutBot's subscriber base by spreading the word in Nigerian student communities.
More subscribers = more students finding opportunities they deserve.

**Time:** 1–2 hours per week.
**Skills needed:** Writing, social media, knowledge of Nigerian student spaces.

### Step-by-step

**WhatsApp groups (highest conversion rate):**
Send this message in every relevant Nigerian student group you belong to:
> ScoutBot is a free bot that scrapes scholarships, fellowships, and internships for
> Nigerian students and sends a curated list every Sunday. No spam. Subscribe here
> (takes 30 seconds): https://docs.google.com/spreadsheets/d/1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s/edit

Follow up 2–3 days later with a screenshot of that week's digest to show it's real.

**Twitter/X — post once per week:**
Feature one opportunity from the current digest:
> [Opportunity name] — open to Nigerian students. Apply by [deadline].
> Full list: https://techhub-extensions.github.io/ScoutBot/
> #Nigeria #scholarship #NigerianStudents

Tag relevant accounts: @YouthHubAfrica, @ScholarshipNG, student union accounts.

**Reddit — post authentically:**
In r/Nigeria, r/scholarships, r/Internships. Don't just drop a link — explain
how ScoutBot has helped you or someone you know.

**Monthly reporting:**
Comment on issue #50 with: which communities you reached, estimated new subscribers,
any feedback heard from students. This helps the team understand what's working.

---

## 4. Issue Triager

**What this role does:**
Keep the GitHub Issues list clean and organised so real bugs and good ideas don't
get buried under noise.

**Time:** 30 minutes every Monday.
**Skills needed:** Basic GitHub navigation. No coding required.

### Triage decision table

| Situation | Action |
|-----------|--------|
| Duplicate of an existing issue | Add `duplicate` label. Comment: "Duplicate of #X." Close. |
| Bug report with enough info | Add `bug` label. Add `good first issue` if it's simple. |
| Bug report missing info | Comment asking for specifics. Add `needs-info` label. |
| Feature request | Add `enhancement` + `help wanted` if reasonable. |
| New source suggestion | Add `new-source` label. Verify it's not already in the spider. |
| Spam / off-topic | Add `invalid` label. Close. |
| No activity for 60+ days | Add `stale`. Comment: "Closing due to inactivity — reopen if still relevant." Close after 7 days. |

**Labels available in this repo:**
`bug`, `enhancement`, `good first issue`, `help wanted`, `new-source`,
`duplicate`, `needs-info`, `invalid`, `stale`

**Rule:** Never close a legitimate issue without a comment explaining why.

### How to add a label
On the issue page, click "Labels" in the right sidebar. Select from the list.

---

## 5. Documentation Writer

**What this role does:**
Keep ScoutBot's documentation accurate and accessible so new contributors can
get started without needing Kamsi's time.

**Time:** 2–4 hours per contribution (not a weekly commitment — contribute when you spot a gap).
**Skills needed:** Clear writing, Markdown syntax. No coding required for most tasks.

### Current documentation status

| File | Status | What it needs |
|------|--------|---------------|
| `README.md` | ✅ Current | — |
| `docs/AI_IMPLEMENTATION.md` | ✅ Current | — |
| `CHANGELOG.md` | ✅ Current | — |
| `CONTRIBUTING.md` | ✅ Good | — |
| `ENGINEERING.md` | Needs updating | Gemini API setup, new pipeline |
| `CODE_REFERENCE.md` | Needs updating | All pipeline classes documented |

### How to contribute a doc improvement

```
1. Fork the repo from https://github.com/TechHub-Extensions/ScoutBot
2. Make your edits to the .md file in any text editor or on GitHub directly
3. Commit with message: "docs: update [filename] — [what changed]"
4. Open a Pull Request
```

**Standards:**
- Use present tense ("The spider scrapes…" not "The spider will scrape…")
- Keep sentences short — readers include students new to open source
- Code examples in triple-backtick blocks with a language hint (```python)
- Update docs in the same PR as any code change that affects them

---

## 6. Data Curator

**What this role does:**
Manually add high-quality opportunities the bot hasn't picked up yet — typically
major scholarships that don't have RSS feeds.

**Time:** 1–2 hours per week.
**Skills needed:** Google Sheets, ability to evaluate opportunity quality.
**Access required:** Ask Kamsi for Google Sheets editor access before starting.

### Step-by-step

**Step 1 — Open the live sheet:**
`https://docs.google.com/spreadsheets/d/1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU/edit`

**Step 2 — Check it's not already listed:**
Press Ctrl+F (or Cmd+F) and search by opportunity name or URL. Skip if found.

**Step 3 — Choose the correct tab:**
- **Nigeria tab** — opportunity specifically for Nigerian students
- **International tab** — open to Africans broadly, or explicitly includes Nigerians

**Step 4 — Add a new row at the bottom of the correct tab:**

| Column | What to enter |
|--------|---------------|
| Title | Full opportunity name (e.g. "NNPC/SNEPCo Postgraduate Scholarship 2026") |
| Link | Direct application URL — NOT a blog post about it |
| Category | Scholarship / Fellowship / Internship / Bootcamp / Grant |
| Deadline | YYYY-MM-DD, or "Rolling" if ongoing, or leave blank if unknown |
| Date Added | Today's date in YYYY-MM-DD format |
| AI Blurb | 1–2 sentences: who should apply and by when |

**Step 5 — Quality check before saving:**
- ✅ Link goes to an actual application page (not a 404 or news article)
- ✅ Deadline is in the future
- ✅ Open to students (not professionals or organisations)
- ✅ Add max 10 entries per week — the Sunday digest shows entries from the last 7 days,
  and flooding it dilutes quality for subscribers

---

## 7. Email Template Designer

**What this role does:**
Improve the HTML email that 500+ subscribers receive every Sunday.
Better design = higher engagement, lower unsubscribes, more opportunities acted on.

**Time:** 2–5 hours per improvement.
**Skills needed:** HTML, inline CSS. Knowledge of email client quirks is helpful.

### Critical constraint: inline CSS only
Gmail strips `<style>` blocks from emails. All CSS must be in `style=""` attributes.
No external stylesheets, no JavaScript (email clients block it), max width 600px.

### How to test changes without sending real emails

```
1. Set up your .env with credentials (see ENGINEERING.md)
2. Run: python run.py --dry-run
3. This writes email_preview.html to the project root
4. Open email_preview.html in your browser
5. Test at mobile width (resize browser to 375px)
6. Test in Gmail browser view before submitting
```

### Where the template lives in notify.py
- `_build_html_email()` — full email structure
- `_opportunity_card()` — single opportunity card
- `_section_header()` — Nigeria / International section dividers

**PR title format:** `feat: improve email template — [what changed]`
Include a screenshot of `email_preview.html` in the PR description.

---

## 8. PR Reviewer

**What this role does:**
Review pull requests from contributors before Kamsi decides to merge. Catch bugs
and give clear, actionable feedback.

**Time:** 1–2 hours per week.
**Skills needed:** Python. Scrapy knowledge helpful but not required.

### Review checklist

For every PR, click "Files changed" and ask:

| Question | If no → action |
|----------|----------------|
| Does it do what the title says? | Ask author to explain extra changes |
| Does it break existing functionality? | Request changes with specifics |
| Are exceptions handled? | Point out unhandled edge cases |
| Does it follow existing code style? | Show the correct pattern from existing code |

### Type-specific checks

| PR type | Check these specifically |
|---------|--------------------------|
| New source URL | Does the URL work in a browser? Is it Cloudflare-free? Not a duplicate? |
| Pipeline change | Is priority order correct (100→150→200)? Exception handling present? |
| Email template change | Tested with `--dry-run`? Renders correctly on mobile? |
| Docs change | Is the information accurate? Does it match current code behaviour? |

### Tone guide
Reviews must be factual and specific, never personal.

- ❌ "This is wrong."
- ✅ "This URL returns a Cloudflare challenge page on GitHub Actions IPs (see issue #34).
  A Google News RSS feed for this source would work better — here's an example of
  the format used in the spider."

---

## 9. QA Tester

**What this role does:**
Verify that ScoutBot works correctly after changes, and write automated tests that
catch regressions before they reach production.

**Time:** 2–4 hours per testing session.
**Skills needed:** Python, pytest basics, ability to read a stack trace.

### Local setup

```
1. Fork and clone the repo
2. pip install -r requirements.txt
3. cp .env.example .env
4. Fill in .env with your own credentials (see ENGINEERING.md)
```

### Manual test checklist

```
# 1. Does the spider produce results?
python run.py --scrape
Check scrapy.log: item_scraped_count should be > 0

# 2. Does cleanup run cleanly?
python run.py --cleanup
Check scoutbot.log: "Removed X rows from 'Nigeria' tab"

# 3. Does the digest build correctly?
python run.py --dry-run
Open email_preview.html: check Nigeria AND International sections both appear

# 4. Does the admin report generate?
python admin_report.py
Check console output for subscriber count and new opportunity stats
```

### Writing new tests
Tests live in `tests/`. Use `unittest.mock` to mock Google Sheets and Gemini API
calls so tests don't require real credentials. Existing test files show the patterns.

**Bug report format for opening a GitHub Issue:**
```
Title: bug: [what broke]

Steps to reproduce:
  python run.py --scrape

Expected: item_scraped_count > 0
Actual: item_scraped_count = 0, item_dropped_count = 15

Full error output: [paste here]
Python version: 3.11.x
OS: Ubuntu 22.04
```

---

## 10. Subscriber Support

**What this role does:**
Handle emails from subscribers who want to unsubscribe, update their email, or ask
questions about the weekly digest.

**Time:** 30 minutes per week (batch all requests on Mondays).
**Skills needed:** Gmail, polite writing.
**Access required:** Kamsi must set up email forwarding or a shared inbox before you start.

### Common requests and how to handle them

| Request | What to do |
|---------|-----------|
| "Please unsubscribe me" | Find their row in the Subscribers tab. Delete it. Reply: "Done — you've been removed." |
| "Not receiving the digest" | Check Subscribers tab (are they listed?) and Bounced tab (are they bounced?). Ask to re-subscribe if bounced via the form. |
| "Can I change my email?" | Delete their old row. Ask them to re-subscribe with the new email via the form. |
| "How do I apply for X opportunity?" | Reply: "ScoutBot surfaces the link — apply directly on the opportunity's website." |
| Bug report or feature idea | Forward to Kamsi and encourage them to open a GitHub issue. |

**Never:**
- Share the subscriber list with anyone outside the core team
- Add anyone to the list without their explicit consent
- Commit to a specific opportunity appearing in a future digest

---

## How to Apply for a Volunteer Role

1. Star the repo: `https://github.com/TechHub-Extensions/ScoutBot`
2. Open an issue with title: `volunteer: interested in [Role Name]`
3. In the issue body, include: your name, location, why you want the role, relevant
   experience (if any), and your available hours per week.
4. Kamsi or a maintainer will respond within 3 days.

**Can start immediately without approval:** Source Hunter, Community Ambassador

**Require a brief intro issue first:** all other roles

---

## What Volunteers Never Have Access To

Managed by the project lead only — never share or request these:

- GitHub Secrets (API keys, passwords, service account credentials)
- Merge access to `main`
- Subscriber list (Subscriber Support role is the only exception, with explicit approval)
- Gemini API key or Gmail App Password

If anyone asks you to share credentials, decline and immediately open a GitHub issue
labelled `security`.
