# ScoutBot

Open-source Python bot that scrapes the internet for opportunities for Nigerian students — scholarships, fellowships, internships, bootcamps, apprenticeships, conferences — across engineering, tech, law, finance, and medicine.

Automatically updates a shared Google Spreadsheet and emails the list to subscribers **twice daily**.

**GitHub:** [TechHub-Extensions/ScoutBot](https://github.com/TechHub-Extensions/ScoutBot)

---

## Features

- Scrapes 15+ opportunity sites (national & international)
- Covers: Scholarships, Fellowships, Internships, Bootcamps, Apprenticeships, Conferences, Grants, Competitions
- Industries: Tech, Engineering, Law, Finance, Medicine, General
- Deduplicates — never adds the same opportunity twice
- Updates Google Sheets automatically in the correct format
- Sends a beautifully formatted HTML email to recipients at **7:00 AM and 7:00 PM daily**
- Fully open-source, 100% Python

---

## Spreadsheet Format

| Title | Industry | Category | Range | Education Level | Organization | Summary | Application Link | Opening Date | Deadline | Status |

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

### 3. Configure credentials

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

```env
SENDER_EMAIL=your-gmail@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
SPREADSHEET_ID=1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
RECIPIENT_EMAILS=email1@gmail.com,email2@gmail.com
```

Place your Google service account JSON file in the project folder, named `service_account.json`.

### 4. Share the Google Sheet

Share your spreadsheet with the service account email  
(from inside the JSON file: `"client_email"`) and give it **Editor** access.

### 5. Run

```bash
# Full pipeline: scrape + update sheet + send email
python run.py

# Run on schedule (scrapes and emails at 7AM + 7PM every day)
python run.py --schedule

# Only scrape/update sheet (no email)
python run.py --scrape

# Only send the email digest
python run.py --notify
```

---

## Credentials Setup

### Gmail App Password

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Enable **2-Step Verification**
3. Search for **App passwords** → create one named "ScoutBot"
4. Use the 16-character code as `GMAIL_APP_PASSWORD`

### Google Service Account

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Enable **Google Sheets API** + **Google Drive API**
3. Create a Service Account → download JSON key → save as `service_account.json`
4. Share the spreadsheet with the service account email (Editor)

---

## Project Structure

```
ScoutBot/
├── run.py                        # Main entry point
├── notify.py                     # Email notification module
├── requirements.txt
├── .env.example                  # Credentials template
├── .gitignore                    # Keeps secrets out of Git
├── scrapy.cfg
└── scoutbot/
    ├── settings.py
    ├── items.py
    ├── pipelines.py               # Dedup + Google Sheets writer
    └── spiders/
        └── opportunities_spider.py  # Main scraping spider
```

---

## Contributing

Pull requests welcome! Add new spider sources in `scoutbot/spiders/opportunities_spider.py` by adding URLs to `start_urls`.

MIT License
