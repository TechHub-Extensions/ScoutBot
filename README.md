# ScoutBot

> An open-source Python bot that automatically scrapes the internet for opportunities for Nigerian students — scholarships, fellowships, internships, bootcamps, apprenticeships, and more — across engineering, tech, law, finance, and medicine. It updates a shared Google Spreadsheet and emails the full list to subscribers **twice daily**.

---

## Why ScoutBot Exists

Opportunities for Nigerian students — especially in tech and engineering — are scattered across dozens of websites with no single reliable source. ScoutBot exists to solve that. It runs quietly in the background, finds new opportunities as they appear, logs them into a shared spreadsheet, and delivers them straight to people's inboxes.

This is a **bot, not a web app**. That is intentional. No dashboard, no login page, no frontend — just a clean, automated Python system that works.

---

## Project Owner & Founder

**Kamsi Richard Ivanna**
Software Engineering Student | Co-Lead, Cowrywise Community LeadCity University

- Email: kamsirichard1960@gmail.com
- LinkedIn: [linkedin.com/in/kamsi-richard-024879257](https://www.linkedin.com/in/kamsi-richard-024879257/)

---

## Core Contact Emails

All project communication goes through email. These are the primary contacts:

| Name | Email | Role |
|------|-------|------|
| Kamsi Richard Ivanna | kamsirichard1960@gmail.com | Founder & Project Lead |
| Tega | tegazion7@gmail.com | Core Team |
| Success | successolamide46@gmail.com | Core Team |
| Ayanfe | ayanfeoluwaalalade2000@gmail.com | Core Team |

To reach the team, email **kamsirichard1960@gmail.com** with subject `[ScoutBot] Your Topic Here`.

---

## Technologies Used

ScoutBot is built entirely in Python. Below is every technology, library, and external service used — what it is, why it was chosen, and what version is in use.

### Language

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11 | Core language. Chosen for its rich ecosystem of scraping, data, and automation libraries. |

### Web Scraping

| Library | Version | Purpose |
|---------|---------|---------|
| **Scrapy** | 2.15.0 | The main scraping engine. An industrial-strength, open-source Python framework for crawling websites and extracting structured data. Handles concurrency, rate-limiting, retries, and pipelines automatically. |
| **lxml** | 6.1.0 | Fast XML/HTML parser. Scrapy uses it internally to parse downloaded pages efficiently. |
| **cssselect** | 1.2.0 | Allows Scrapy to use CSS selectors (like `h2 a::text`) to target HTML elements. |
| **requests** | 2.33.1 | HTTP library used for direct HTTP calls (e.g. health checks and utility scripts). Scrapy handles most requests internally. |

### Google Sheets Integration

| Library | Version | Purpose |
|---------|---------|---------|
| **gspread** | 6.2.1 | Python client for the Google Sheets API. Used to read existing rows and append new opportunities to the spreadsheet. |
| **google-auth** | 2.49.2 | Google's official authentication library. Handles OAuth2 credentials for the service account that accesses Google Sheets. |
| **google-auth-oauthlib** | 1.2.0 | Adds OAuth 2.0 flow support to google-auth. Required by gspread for service account authentication. |
| **google-auth-httplib2** | 0.2.0 | HTTP transport adapter for google-auth. Allows the Google API client to make authenticated requests. |
| **google-api-python-client** | 2.127.0 | Google's official Python client for all Google APIs. Provides the underlying transport for Sheets and Drive access. |

### Email

| Tool | Version | Purpose |
|------|---------|---------|
| **smtplib** | Built-in | Python's built-in library for sending emails via SMTP. No installation needed. |
| **email.mime** | Built-in | Python's built-in module for constructing email messages with HTML content and proper encoding. |
| **Gmail SMTP** | — | Email delivery service. ScoutBot logs in to Gmail via App Password and sends emails through Gmail's SMTP server (`smtp.gmail.com:465`). Free and reliable. |

### Scheduling & Automation

| Library | Version | Purpose |
|---------|---------|---------|
| **schedule** | 1.2.2 | Lightweight Python job scheduler. Used to trigger the full pipeline at 7:00 AM and 7:00 PM every day. Simple, no external dependencies. |

### Configuration & Security

| Library | Version | Purpose |
|---------|---------|---------|
| **python-dotenv** | 1.2.2 | Loads environment variables from a `.env` file into the Python runtime. Keeps all credentials (passwords, API keys) out of source code. |

### External Services

| Service | Purpose |
|---------|---------|
| **Google Sheets API** | Stores all scraped opportunities in a shared, human-readable spreadsheet |
| **Google Drive API** | Required alongside Sheets API for service account access |
| **Google Service Account** | A non-human Google account that authenticates the bot's access to Sheets without needing a user to log in |

### Development Tools

| Tool | Purpose |
|------|---------|
| **Git** | Version control |
| **GitHub** | Repository hosting at [TechHub-Extensions/ScoutBot](https://github.com/TechHub-Extensions/ScoutBot) |
| **python-dotenv** | Manages credentials safely in `.env` files |
| **.gitignore** | Prevents secrets (`.env`, `service_account.json`) from being committed to GitHub |

---

## What It Does

1. **Scrapes** 15+ opportunity websites (national and international) using Scrapy
2. **Deduplicates** — never adds the same opportunity twice
3. **Updates** a shared Google Spreadsheet in a standardised format
4. **Emails** a formatted HTML digest to all subscribers at **7:00 AM and 7:00 PM** every day

### Categories Covered
Scholarships · Fellowships · Internships · Bootcamps · Apprenticeships · Conferences · Grants · Competitions · Awards

### Industries Covered
Tech · Engineering · Law · Finance · Medicine · General

### Sources Scraped
- afterschoolafrica.com
- opportunitydesk.org
- opportunitiesforafricans.com
- scholars4dev.com
- scholarshipregion.com
- scholarshipair.com
- opportunities.youthhubafrica.org
- myschoolng.com
- *(contributors can add more — see CONTRIBUTING.md)*

---

## Spreadsheet Format

Every row in the Google Sheet follows this structure:

| Column | Description |
|--------|-------------|
| Title | Name of the opportunity |
| Industry | Tech / Engineering / Law / Finance / Medicine / General |
| Category | Scholarship / Fellowship / Internship / Bootcamp / etc. |
| Range | National (Nigeria) or International |
| Education Level | Bachelor / Masters / PhD / HND/OND / Any |
| Organization | Name of the awarding body |
| Summary | Brief description (max 400 chars) |
| Application Link | Direct URL to apply |
| Opening Date | When applications opened |
| Deadline | Application deadline |
| Status | Open / Closed |

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/TechHub-Extensions/ScoutBot.git
cd ScoutBot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
SENDER_EMAIL=your-gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
SPREADSHEET_ID=1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
RECIPIENT_EMAILS=email1@gmail.com,email2@gmail.com
```

Place your Google service account JSON file in the project folder as `service_account.json`.

> **Never commit `.env` or `service_account.json` to Git.** They are listed in `.gitignore`.

### 4. Run

```bash
# Full pipeline: scrape → update sheet → send email
python run.py

# Run on schedule (7AM + 7PM every day — recommended for production)
python run.py --schedule

# Only scrape and update the sheet
python run.py --scrape

# Only send the email digest
python run.py --notify
```

---

## Adding Email Recipients

Open `.env` and add the new email to `RECIPIENT_EMAILS`, separated by commas:

```env
RECIPIENT_EMAILS=kamsirichard1960@gmail.com,newperson@gmail.com
```

No code changes needed.

---

## Credential Setup Guides

### Gmail App Password

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Enable **2-Step Verification** (Security tab)
3. Search for **App passwords**
4. Create one named "ScoutBot" — copy the 16-character code
5. Set it as `GMAIL_APP_PASSWORD` in your `.env`

### Google Service Account (for Sheets access)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create or select a project
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to Credentials → Create Credentials → Service Account
5. Download the JSON key → save as `service_account.json` in the project folder
6. Share your spreadsheet with the service account `client_email` → set as **Editor**

---

## Project Structure

```
ScoutBot/
├── run.py                             # Main entry point
├── notify.py                          # Reads sheet, builds and sends email digest
├── requirements.txt                   # Python dependencies with pinned versions
├── .env.example                       # Credentials template (safe to commit)
├── .env                               # Your actual credentials (gitignored)
├── service_account.json               # Google service account key (gitignored)
├── .gitignore
├── scrapy.cfg                         # Scrapy project configuration
├── setup_cron.py                      # Optional: sets up a cron job
├── README.md                          # This file
├── CONTRIBUTING.md                    # How to contribute
├── CODE_REFERENCE.md                  # Every class, function, and variable explained
└── scoutbot/                          # Scrapy project package
    ├── __init__.py
    ├── items.py                       # Data field definitions (OpportunityItem)
    ├── pipelines.py                   # DedupePipeline + SheetsPipeline
    ├── settings.py                    # Scrapy engine configuration
    └── spiders/
        ├── __init__.py
        └── opportunities_spider.py    # Main scraping spider
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide — how to add sources, submit pull requests, and the project's code of conduct.

---

## License

MIT License — free to use, modify, and distribute with attribution.
