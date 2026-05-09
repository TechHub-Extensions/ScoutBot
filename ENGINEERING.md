# ScoutBot — Engineering Reference

**Author:** Kamsi Richard Ivanna  
**Role:** Co-lead, Cowrywise Ambassador Community · Lead City University  
**Repo:** https://github.com/TechHub-Extensions/ScoutBot  
**Last updated:** May 2026

---

## Table of Contents

1. [What ScoutBot Does](#1-what-scoutbot-does)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Data Flow — Step by Step](#3-data-flow--step-by-step)
4. [The Spider — How Scraping Works](#4-the-spider--how-scraping-works)
5. [The Pipeline — Dedup & Google Sheets](#5-the-pipeline--dedup--google-sheets)
6. [Cleanup — Removing Stale Entries](#6-cleanup--removing-stale-entries)
7. [Notify — The Email Digest](#7-notify--the-email-digest)
8. [Welcome — Onboarding New Subscribers](#8-welcome--onboarding-new-subscribers)
9. [Subscriber Management](#9-subscriber-management)
10. [Scheduling & GitHub Actions](#10-scheduling--github-actions)
11. [Secrets & Credentials](#11-secrets--credentials)
12. [Timing — Nigerian Time (WAT)](#12-timing--nigerian-time-wat)
13. [Opportunity Sources](#13-opportunity-sources)
14. [Inference Engine — How Categories Are Assigned](#14-inference-engine--how-categories-are-assigned)
15. [Error Handling & Resilience](#15-error-handling--resilience)
16. [Running Locally](#16-running-locally)
17. [File Map](#17-file-map)

---

## 1. What ScoutBot Does

ScoutBot is a fully automated Python bot that:

- **Scrapes 15+ opportunity websites** twice a day, collecting scholarships, fellowships, internships, bootcamps, grants, VC funding, accelerators, and more — including opportunities for Africans in Asia.
- **Writes new, non-duplicate entries** to a shared Google Sheets spreadsheet in real time.
- **Removes expired listings** — any opportunity whose deadline has passed is deleted from the sheet before the email goes out.
- **Emails an HTML digest** to 518+ Nigerian students and founders at **7 AM and 7 PM WAT** every day, individually addressed so no subscriber sees any other subscriber's email address.
- **Sends a welcome email** to every subscriber every 2 days, introducing ScoutBot and the opportunity sheet.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Actions CI                       │
│  cron: 06:00 UTC (07:00 WAT) and 18:00 UTC (19:00 WAT)      │
└──────────────────────────┬──────────────────────────────────┘
                           │  triggers
                           ▼
┌──────────────────────────────────────────────────────────────┐
│  run.py  (full pipeline orchestrator)                         │
│                                                              │
│  Step 1 ─► Spider (Scrapy)  ─────────────────────────────┐  │
│                                                           │  │
│  Step 2 ─► Cleanup (gspread) ◄──────── Google Sheets ◄───┤  │
│                                              ▲            │  │
│  Step 3 ─► Notify (smtplib)                 │            │  │
│              │                              └────────────┘  │
│              ▼                              Pipeline writes  │
│         Gmail SMTP ──► 518 individual emails                 │
└──────────────────────────────────────────────────────────────┘

Separate workflow (every 2 days):
  welcome.py ──► Gmail SMTP ──► 518 individual welcome emails
```

The whole stack is **serverless** — it runs inside GitHub Actions (free tier) with no server to maintain. The only persistent state lives in Google Sheets.

---

## 3. Data Flow — Step by Step

```
[15+ websites]
      │
      │  HTTP GET (Scrapy)
      ▼
[Spider parses listing pages]
      │
      │  follow links → individual opportunity pages
      ▼
[parse_opportunity()]
      │
      ├─ extract title, deadline, text, apply link, organization
      ├─ infer: industry, category, range, education level
      ├─ is_expired()? → DROP if deadline is past
      ├─ past year in title? → DROP
      └─ yield OpportunityItem
      │
      ▼
[DedupePipeline]
      │  drops anything whose URL was already seen this run
      ▼
[SheetsPipeline]
      │  loads existing URLs from Google Sheets into memory
      │  drops items already in the sheet
      │  batches new rows → sheet.append_rows()
      ▼
[Google Sheets — sheet1 / "Opportunities"]
      │
      ▼
[cleanup.py]
      │  reads all rows
      │  parses Deadline column with dateutil
      │  deletes rows where deadline < today OR status == "Closed"
      │  deletes from bottom-up (so row indices don't shift mid-delete)
      ▼
[notify.py]
      │  reads last 30 rows
      │  builds HTML digest
      │  fetches recipient list from:
      │    - Google Form responses sheet (col D)
      │    - Subscribers tab (col B)
      │    - RECIPIENT_EMAILS env var
      │  deduplicates all three sources
      │  sends individual email per subscriber
      │  batches: 30 recipients / batch, 6-min pause between batches
      ▼
[518 individual Gmail deliveries]
```

---

## 4. The Spider — How Scraping Works

**Framework:** [Scrapy](https://scrapy.org/) — Python's most battle-tested scraping framework.

**File:** `scoutbot/spiders/opportunities_spider.py`

### 4.1 How a crawl works

1. Scrapy visits every URL in `start_urls` (listing/category pages).
2. `parse()` extracts all article links from the page using CSS selectors:
   ```
   article h2.entry-title a
   article h3.entry-title a
   .entry-title a
   h2.post-title a
   ```
3. Each link is followed to `parse_opportunity()` — the individual opportunity page.
4. Pagination: up to 3 pages deep per source (`MAX_PAGES = 3`), following `a.next.page-numbers`.

### 4.2 Date filtering (stale entry prevention)

The spider filters at **three levels**, before anything reaches the sheet:

| Level | Check | Action |
|---|---|---|
| URL | Link contains a year < current year (e.g. `2024`) | Skip — don't even visit |
| Title | Title explicitly names a past year (e.g. "2024 Chevening Scholarship") | Drop item |
| Deadline | Parsed deadline date < today | Drop item |

`is_expired()` uses `python-dateutil` to parse fuzzy date strings like "15 June 2025" or "March 31, 2024" into real `date` objects for comparison.

### 4.3 What gets extracted per opportunity

| Field | How it's extracted |
|---|---|
| `title` | `h1.entry-title`, `h1.post-title`, or `<title>` tag |
| `industry` | Keyword match against title + body text |
| `category` | Keyword match (ordered priority list) against URL + body |
| `range` | International vs National — keyword match |
| `education_level` | PhD / Masters / Bachelor / HND/OND / Any — keyword match |
| `organization` | `og:site_name` meta tag, or domain name as fallback |
| `summary` | First 400 characters of `<p>` tags in the article body |
| `application_link` | URL of the opportunity page itself |
| `deadline` | Regex patterns: "deadline: June 30 2025", "apply by…", "closes…" |
| `status` | Always "Open" at write time — cleanup.py handles expiry later |

### 4.4 Search URL handling

Asia and keyword-specific searches use `?s=` query URLs (e.g. `?s=china+scholarship+africa`). These are handled differently — pagination is **not** applied to search results to avoid infinite crawls.

---

## 5. The Pipeline — Dedup & Google Sheets

**File:** `scoutbot/pipelines.py`

Scrapy pipelines process every item the spider yields, in sequence.

### DedupePipeline

Maintains a Python `set()` of URLs seen **in this run**. If the same URL appears twice (common when multiple source sites link the same opportunity), the duplicate is dropped with `DropItem`.

### SheetsPipeline

1. **On open:** Connects to Google Sheets via a service account, reads all existing `Application Link` values into a `set`. This is the cross-run dedup — prevents re-adding opportunities already in the sheet.
2. **Per item:** If the URL is already in the sheet set, drop it. Otherwise append to a buffer.
3. **On close:** Calls `sheet.append_rows(buffer)` in a single API call to minimize quota usage. Uses `USER_ENTERED` mode so dates and formulas in cells are interpreted correctly.

**Google Sheets authentication:** Uses a service account JSON key (`service_account.json`) with OAuth2 scopes for Sheets + Drive. The key is stored as a base64-encoded GitHub Secret and decoded fresh each run.

---

## 6. Cleanup — Removing Stale Entries

**File:** `cleanup.py`

Runs **after** the spider, **before** the email is sent.

### Logic

```python
for each row in sheet (skipping header):
    if status == "Closed":
        mark for deletion
    elif deadline can be parsed AND deadline < today:
        mark for deletion

delete marked rows from bottom-up
# (bottom-up is critical — deleting row 5 shifts row 6 to row 5,
#  so you always delete the highest index first)
```

### What is kept (not deleted)

- Rows where deadline says "Ongoing", "Rolling", "TBD", "Open", "N/A", "—"
- Rows where the deadline field is empty or unparseable
- Any row with a future deadline

---

## 7. Notify — The Email Digest

**File:** `notify.py`

### 7.1 What gets emailed

The **30 most recently added rows** from the Google Sheet, reversed so newest appears at the top. Each opportunity is rendered as a colour-coded table row:

| Category | Colour |
|---|---|
| Scholarship | Navy blue |
| Fellowship | Purple |
| Internship | Teal |
| Grant | Dark green |
| VC Funding | Dark red |
| Accelerator | Crimson |
| Pitch Competition | Deep red |
| Bootcamp | Gold |

### 7.2 Privacy model

Every subscriber receives a **separate, individually addressed email** — their address is the only one in the `To:` field. This means:
- No subscriber can see any other subscriber's address
- No BCC header (which some spam filters flag)
- No group send artefacts in the sender's Sent folder

### 7.3 Gmail rate limit handling

Gmail App Passwords allow roughly 500 emails per day on a standard account. ScoutBot batches sends:

- **Batch size:** 30 recipients per SMTP connection
- **Pause between batches:** 6 minutes (360 seconds)
- **Total time for 518 subscribers:** ~17 batches × 6 min = ~100 minutes

This is why the GitHub Actions workflow has a **120-minute timeout**.

### 7.4 SMTP connection

Uses `smtplib.SMTP_SSL("smtp.gmail.com", 465)` — a direct TLS connection (not STARTTLS). One connection is opened per batch and reused for all 30 sends in that batch, then closed cleanly.

---

## 8. Welcome — Onboarding New Subscribers

**File:** `welcome.py`

Runs **every 2 days** via its own GitHub Actions workflow (`welcome.yml`). Sends a rich HTML introduction email to every subscriber explaining:
- What ScoutBot is and who runs it
- How to access the full opportunity sheet
- What types of opportunities are covered
- The fundraising doc link
- The vibecoded disclaimer

Same batching and privacy model as the digest.

---

## 9. Subscriber Management

Subscribers come from three sources, merged and deduplicated on every run:

| Source | Where | Column | Start row |
|---|---|---|---|
| Google Form responses | Spreadsheet ID: `1dFcnVvQjWkuYhN...` | D (col 4) | Row 2 |
| Subscribers tab | Main spreadsheet, "Subscribers" tab | B (col 2) | Row 3 |
| Environment variable | `RECIPIENT_EMAILS` (comma-separated) | — | — |

Deduplication is case-insensitive and order-preserving. Form responses come first so anyone who just signed up is included in the very next run.

**Current count:** 518 unique subscribers (as of May 2026).

---

## 10. Scheduling & GitHub Actions

### scoutbot.yml — Main digest

```
Cron: 0 6 * * *    →  06:00 UTC = 07:00 WAT (7 AM Nigeria)
Cron: 0 18 * * *   →  18:00 UTC = 19:00 WAT (7 PM Nigeria)
```

Steps:
1. Checkout repo
2. Set up Python 3.11 (cached pip)
3. Install `requirements.txt`
4. Decode `GOOGLE_SERVICE_ACCOUNT_JSON_B64` secret → `service_account.json`
5. Write `.env` file from secrets
6. `python run.py` — full pipeline
7. Upload `scoutbot.log` + `scrapy.log` as artifacts (kept 7 days)

### welcome.yml — Welcome email

```
Cron: 0 7 1,3,5,7,9,... * *   →  07:00 UTC = 08:00 WAT (8 AM Nigeria, odd days)
```

Same setup steps, runs `python welcome.py`.

### Manual trigger

Both workflows support `workflow_dispatch` — you can trigger them manually from the GitHub Actions tab at any time without waiting for the cron.

---

## 11. Secrets & Credentials

All credentials live in **GitHub Actions Secrets** — never committed to the repo.

| Secret name | What it contains |
|---|---|
| `SENDER_EMAIL` | `kamsirichard1960@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmail App Password (16-char, spaces stripped) |
| `GOOGLE_SERVICE_ACCOUNT_JSON_B64` | `service_account.json` base64-encoded |
| `SPREADSHEET_ID` | Main Google Sheets ID |
| `RECIPIENT_EMAILS` | Comma-separated fallback email list |

The service account (`scoutbot-service@opportunties-bot.iam.gserviceaccount.com`) has editor access to both spreadsheets. It was created in Google Cloud Console and the key was downloaded as JSON, then base64-encoded before being stored as a secret.

---

## 12. Timing — Nigerian Time (WAT)

Nigeria operates on **West Africa Time (WAT) = UTC+1** year-round (no daylight saving).

| Event | WAT | UTC | Cron (UTC) |
|---|---|---|---|
| Morning digest | 07:00 | 06:00 | `0 6 * * *` |
| Evening digest | 19:00 | 18:00 | `0 18 * * *` |
| Welcome email | 08:00 | 07:00 | `0 7 1,3,5,...` |

**Important:** GitHub Actions cron jobs always run in UTC. The offset of exactly 1 hour means the crons above must use the UTC equivalent, not the WAT time. Previously the `--schedule` mode in `run.py` used "07:00" and "19:00" raw — on a UTC server this fired 1 hour late (08:00 and 20:00 WAT). This was fixed to use "06:00" and "18:00" UTC.

**Note on GitHub Actions timing:** GitHub Actions can fire scheduled jobs up to 15–30 minutes late during periods of high platform load. This is a platform limitation and cannot be avoided. If exact timing matters, a dedicated VPS/cron is more reliable.

---

## 13. Opportunity Sources

### Africa-focused (general)

| Site | Categories scraped |
|---|---|
| scholars4dev.com | Scholarships for Africans |
| opportunitiesforafricans.com | Scholarships, Fellowships, Internships, Grants, Competitions, Entrepreneurship |
| afterschoolafrica.com | Scholarships, Fellowships, Internships, Competitions, Grants, Business |
| opportunitydesk.org | Scholarships, Fellowships, Internships, Grants, Awards, Competitions, Entrepreneurship |
| scholarshipregion.com | Nigeria scholarships |
| myschoolng.com | Nigeria scholarships |
| youthhubafrica.org | Scholarships, Fellowships, Internships, Grants, Competitions |

### Asia-specific (for Africans/Nigerians)

| Site | Region |
|---|---|
| scholars4dev.com/category/scholarships-in-asia/ | Pan-Asia |
| scholars4dev.com/category/scholarships-in-china/ | China (CSC scholarship) |
| scholars4dev.com/category/scholarships-in-japan/ | Japan (MEXT) |
| scholars4dev.com/category/scholarships-in-south-korea/ | Korea (KGSP) |
| scholars4dev.com/category/scholarships-in-india/ | India (ICCR) |
| opportunitydesk.org/?s=china+scholarship+africa | China |
| opportunitydesk.org/?s=japan+scholarship+africa | Japan |
| opportunitydesk.org/?s=asian+development+bank | ADB |
| opportunitiesforafricans.com/?s=china/japan/korea/india | Asia (4 searches) |
| afterschoolafrica.com/?s=china/japan/korea+scholarship | Asia (3 searches) |
| youthhubafrica.org/?s=china/japan/korea | Asia (3 searches) |

### Startup / funding

| Site | Categories scraped |
|---|---|
| opportunitydesk.org | Grants, Awards, Competitions, Entrepreneurship |
| opportunitiesforafricans.com | Grants, Competitions, Entrepreneurship |
| afterschoolafrica.com | Grants, Business |
| youthhubafrica.org | Grants, Competitions |

---

## 14. Inference Engine — How Categories Are Assigned

The spider has no ML. All classification is rule-based keyword matching on the combined title + body text.

### Industry

Matched in order. First match wins:

```
Startup   → "startup", "founder", "accelerator", "incubator", "vc fund", ...
Tech      → "tech", "software", "coding", "ai", "blockchain", ...
Engineering → "engineer", "civil", "electrical", "petroleum", ...
Law       → "law", "legal", "llb", "barrister", ...
Finance   → "finance", "economics", "banking", "investment", ...
Medicine  → "medicine", "health", "pharma", "clinical", ...
General   → (default if nothing matches)
```

### Category

Ordered pattern list (URL + text). Higher entries take priority:

```
"venture capital" → VC Funding
"incubator"       → Incubator
"accelerator"     → Accelerator
"pitch competition" → Pitch Competition
"hackathon"       → Pitch Competition
"scholarship"     → Scholarship
"fellowship"      → Fellowship
"internship"      → Internship
"bootcamp"        → Bootcamp
"grant"           → Grant
"conference"      → Conference
...
```

### Range

```
"international", "fully funded", "study abroad", "china", "japan",
"korea", "asia", "mext", "kgsp", "iccr", "adb"  →  International
(everything else)                                 →  National
```

### Education Level

```
"phd", "doctoral"         → PhD
"masters", "msc", "mba"   → Masters
"hnd", "ond"              → HND/OND
"bachelor", "undergraduate" → Bachelor
"any level", "open to all" → Any
(Startup industry default) → Any
(everything else)          → Bachelor
```

---

## 15. Error Handling & Resilience

| Scenario | What happens |
|---|---|
| A source website is down | Scrapy logs the error, skips that URL, continues with the rest |
| Google Sheets API quota hit | `SheetsPipeline` logs the error, items for that run are not written |
| Gmail rate limit hit | Per-email exceptions are caught, logged, and skipped — the batch continues |
| Deadline unparseable | `is_expired()` returns False → item is kept (safe default) |
| Service account JSON missing | `SheetsPipeline.open_spider()` sets `self.sheet = None`, all items pass through silently |
| GitHub Actions runner slow | 120-minute timeout gives the full 518-subscriber send plenty of headroom |

---

## 16. Running Locally

```bash
cd scoutbot

# Install dependencies
pip install -r requirements.txt

# Set up .env (copy from .env.example and fill in)
cp .env.example .env

# Full pipeline (scrape → cleanup → email)
python run.py

# Only scrape (update sheet, no email)
python run.py --scrape

# Only remove expired rows from sheet
python run.py --cleanup

# Only send email
python run.py --notify

# Run on schedule — 07:00 and 19:00 WAT every day
python run.py --schedule
```

**Required `.env` variables:**

```
SENDER_EMAIL=kamsirichard1960@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
SPREADSHEET_ID=1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU
FORM_SHEET_ID=1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
RECIPIENT_EMAILS=you@example.com,other@example.com
```

---

## 17. File Map

```
scoutbot/
├── run.py                          # Main pipeline orchestrator + local scheduler
├── notify.py                       # Email digest builder + sender
├── welcome.py                      # Welcome email + sender
├── cleanup.py                      # Removes expired rows from Google Sheets
├── requirements.txt                # Python dependencies
├── scrapy.cfg                      # Scrapy project config
├── service_account.json            # Google service account key (NOT committed)
├── .env                            # Local credentials (NOT committed)
│
├── scoutbot/                       # Scrapy project package
│   ├── settings.py                 # Scrapy settings (pipelines, concurrency, etc.)
│   ├── items.py                    # OpportunityItem field definitions
│   ├── pipelines.py                # DedupePipeline + SheetsPipeline
│   └── spiders/
│       └── opportunities_spider.py # The main spider (all sources + inference)
│
└── .github/
    └── workflows/
        ├── scoutbot.yml            # Twice-daily digest (07:00 + 19:00 WAT)
        └── welcome.yml             # Welcome email (every 2 days, 08:00 WAT)
```

---

*ScoutBot is open source — contributions welcome at https://github.com/TechHub-Extensions/ScoutBot*
