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

To reach the team, email **kamsirichard1960@gmail.com** with the subject line `[ScoutBot] Your Topic Here`.

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
- *(and more — contributors can add sources)*

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

To add a new subscriber to the email digest, open `.env` and add their email to the `RECIPIENT_EMAILS` list, separated by commas:

```env
RECIPIENT_EMAILS=kamsirichard1960@gmail.com,newperson@gmail.com,another@gmail.com
```

That's it. No code changes needed.

---

## Credential Setup Guides

### Gmail App Password

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Enable **2-Step Verification** (Security tab)
3. Search for **App passwords** at the top
4. Create one named "ScoutBot" — copy the 16-character code
5. Paste it as `GMAIL_APP_PASSWORD` in your `.env`

### Google Service Account (for Sheets access)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create or select a project
3. Enable **Google Sheets API** and **Google Drive API** under APIs & Services → Library
4. Go to APIs & Services → Credentials → Create Credentials → Service Account
5. Download the JSON key → save as `service_account.json` in the project folder
6. Open your Google Spreadsheet → Share → paste the service account's `client_email` → set role to **Editor**

---

## Project Structure

```
ScoutBot/
├── run.py                             # Main entry point
├── notify.py                          # Reads sheet, builds and sends email digest
├── requirements.txt                   # Python dependencies
├── .env.example                       # Credentials template (safe to commit)
├── .env                               # Your actual credentials (gitignored)
├── service_account.json               # Google service account key (gitignored)
├── .gitignore
├── scrapy.cfg                         # Scrapy project configuration
├── setup_cron.py                      # Optional: sets up a cron job
├── README.md                          # This file
├── CONTRIBUTING.md                    # How to contribute
└── scoutbot/                          # Scrapy project package
    ├── __init__.py
    ├── items.py                       # Data field definitions (OpportunityItem)
    ├── pipelines.py                   # DedupePipeline + SheetsPipeline
    ├── settings.py                    # Scrapy settings and configuration
    └── spiders/
        ├── __init__.py
        └── opportunities_spider.py   # Main scraping spider
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contribution guide — including how to add new sources, how to submit pull requests, and the project's code of conduct.

---

## License

MIT License — free to use, modify, and distribute.
