# ScoutBot

> An open-source Python bot that automatically scrapes the internet for opportunities for Nigerian students — scholarships, fellowships, internships, bootcamps, apprenticeships, and more — across engineering, tech, law, finance, and medicine. It updates a shared Google Spreadsheet and emails the full list to subscribers **twice daily**.

---

## 📬 Subscribe — Get Opportunities in Your Inbox (Free)

ScoutBot emails a curated digest of the latest opportunities at **7:00 AM and 7:00 PM Lagos time, every day**.

**To subscribe**, fill in the subscription form — you will be picked up automatically at the next run:

> **[→ Fill the ScoutBot Subscription Form](https://docs.google.com/spreadsheets/d/1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s/edit?gid=1666713039#gid=1666713039)**

No app, no login, no fee. One form fill and you are on the list.

📋 [View the live opportunity spreadsheet →](https://docs.google.com/spreadsheets/d/1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU/edit)

---

## 💛 Support ScoutBot

ScoutBot is open source and free for every user. We are Nigerian students building this with zero budget.

**Our goal:** reach **4,000 Nigerian students** in the next 6 months.
To get there we need **₦2,000,000 (~$1,500 USD)** for Twitter/X advertising.

For all financial information — goals, cost breakdown, how to contribute, and account details — see the fundraising brief:

📄 **[ScoutBot — Fundraising & Support Brief (Google Doc)](https://docs.google.com/document/d/1SqxaAg4tvuWp3LgGzqSSSw4_bxBWHmgmrQ9IyyKHtE8/edit)**

---

### Contribute Code / Non-Financially

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide.

Quick ways to help:
- ⭐ **Star this repository** (takes 2 seconds, means a lot)
- 🔀 Fork and open a pull request — add new sources, fix bugs, improve the email design
- 🐛 Open a GitHub Issue to report bugs or suggest features
- 📣 Share ScoutBot with Nigerian student WhatsApp groups, Discord servers, and Twitter/X communities

---

## Why ScoutBot Exists

Opportunities for Nigerian students — especially in tech and engineering — are scattered across dozens of websites with no single reliable source. ScoutBot exists to solve that. It runs quietly in the background, finds new opportunities as they appear, logs them into a shared spreadsheet, and delivers them straight to people's inboxes.

This is a **bot, not a web app**. That is intentional. No dashboard, no login page, no frontend — just a clean, automated Python system that works.

---

## The Founding Team

| Name | Email | Role |
|------|-------|------|
| **Kamsi Richard Ivanna** | kamsirichard1960@gmail.com | Founder & Project Lead |
| Tega | tegazion7@gmail.com | Core Team |
| olamide | successolamide@gmail.com | Whatsapp Intiative - Core Team |
| Ibukun Ojo | adeojoibukun28@gmail.com | Core Team |
| David Macaulay | macaulaydavid999@gmail.com | Core Team |

To reach the team, email **kamsirichard1960@gmail.com** with subject `[ScoutBot] Your Topic Here`.

Kamsi's LinkedIn: [linkedin.com/in/kamsi-richard-024879257](https://www.linkedin.com/in/kamsi-richard-024879257/)

---

## Technologies Used

ScoutBot is built entirely in Python.

### Language

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11 | Core language. Chosen for its rich ecosystem of scraping, data, and automation libraries. |

### Web Scraping

| Library | Version | Purpose |
|---------|---------|---------|
| **Scrapy** | 2.15.0 | Industrial-strength crawling framework. Handles concurrency, rate-limiting, retries, and pipelines automatically. |
| **lxml** | 6.1.0 | Fast XML/HTML parser used by Scrapy internally. |
| **cssselect** | 1.2.0 | Allows Scrapy to use CSS selectors to target HTML elements. |
| **requests** | 2.33.1 | HTTP library for direct HTTP calls and utility scripts. |

### Google Integration

| Library | Version | Purpose |
|---------|---------|---------|
| **gspread** | 6.2.1 | Python client for the Google Sheets API. |
| **google-auth** | 2.49.2 | Google's official authentication library for service account credentials. |
| **google-auth-oauthlib** | 1.2.0 | OAuth 2.0 flow support for google-auth. |
| **google-auth-httplib2** | 0.2.0 | HTTP transport adapter for google-auth. |
| **google-api-python-client** | 2.127.0 | Google's official Python client (Sheets, Drive, Docs APIs). |

### Email

| Tool | Version | Purpose |
|------|---------|---------|
| **smtplib** | Built-in | Sends emails via SMTP. |
| **email.mime** | Built-in | Constructs HTML email messages. |
| **Gmail SMTP** | — | `smtp.gmail.com:465`. Each subscriber receives a **personally addressed email** — nobody can see anyone else's address. |

### Scheduling & Config

| Library | Version | Purpose |
|---------|---------|---------|
| **schedule** | 1.2.2 | Lightweight Python job scheduler for 7 AM / 7 PM runs. |
| **python-dotenv** | 1.2.2 | Loads credentials from `.env` — keeps secrets out of source code. |

### External Services

| Service | Purpose |
|---------|---------|
| **Google Sheets API** | Stores scraped opportunities and the subscriber list |
| **Google Docs API** | Maintains the fundraising brief document |
| **Google Drive API** | Service account access alongside Sheets |
| **Google Forms** | Subscription form — responses are read automatically before every email run |

---

## What It Does

1. **Scrapes** 15+ opportunity websites using Scrapy
2. **Deduplicates** — never adds the same opportunity twice
3. **Updates** the shared Google Spreadsheet
4. **Reads** the Google Form responses + Subscribers tab before every send — new sign-ups are included automatically in the next run
5. **Emails** a personal, individually addressed digest to every subscriber at **7:00 AM and 7:00 PM** daily

> **Privacy:** Each subscriber receives their own email where only their address appears. No one can see any other subscriber's email.

### Categories Covered

**For students:** Scholarships · Fellowships · Internships · Bootcamps · Apprenticeships · Conferences · Awards

**For startups & founders:** Grants · VC Funding · Accelerators · Incubators · Pitch Competitions · Hackathons · Innovation Awards

### Industries Covered
Startup · Tech · Engineering · Law · Finance · Medicine · General

### Sources Scraped

**Student opportunities**
- afterschoolafrica.com — scholarships, fellowships, internships, competitions
- opportunitydesk.org — scholarships, fellowships, internships
- opportunitiesforafricans.com — scholarships, fellowships, internships
- scholars4dev.com — international scholarships for Africans
- scholarshipregion.com — Nigerian scholarships
- opportunities.youthhubafrica.org — youth-focused opportunities
- myschoolng.com — Nigerian student scholarships

**Startup funding** *(grants, VC, accelerators, incubators, pitch comps)*
- opportunitydesk.org — grants, awards, competitions, entrepreneurship
- opportunitiesforafricans.com — grants, competitions, entrepreneurship
- afterschoolafrica.com — grants, business opportunities
- opportunities.youthhubafrica.org — grants, competitions

*(contributors can add more — see CONTRIBUTING.md)*

---

## Spreadsheet Format

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
FORM_SHEET_ID=1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
RECIPIENT_EMAILS=email1@gmail.com,email2@gmail.com
```

Place your Google service account JSON file as `service_account.json`.

> **Never commit `.env` or `service_account.json` to Git.** They are listed in `.gitignore`.

### 4. Run

```bash
# Full pipeline: scrape → update sheet → send email
python run.py

# Run on schedule (7AM + 7PM every day)
python run.py --schedule

# Only scrape and update the sheet
python run.py --scrape

# Only send the email digest
python run.py --notify
```

---

## Production Schedule (GitHub Actions)

ScoutBot runs **automatically twice every day** via GitHub Actions — no server or hosting needed.

| Time (Lagos / WAT) | UTC | What happens |
|--------------------|-----|--------------|
| 07:00 AM | 06:00 | Scrape → cleanup closed → read new form subscribers → email digest |
| 07:00 PM | 18:00 | Scrape → cleanup closed → read new form subscribers → email digest |

Trigger manually: **Actions tab → "ScoutBot — Twice-Daily Run" → Run workflow**

### Required GitHub Secrets

| Secret name | What it holds |
|-------------|---------------|
| `SENDER_EMAIL` | Gmail address used to send the digest |
| `GMAIL_APP_PASSWORD` | Gmail 16-character app password (no spaces) |
| `SPREADSHEET_ID` | The main Google Sheet ID |
| `FORM_SHEET_ID` | The Google Form responses Sheet ID |
| `RECIPIENT_EMAILS` | Fallback comma-separated recipient list |
| `GOOGLE_SERVICE_ACCOUNT_JSON_B64` | Base64-encoded `service_account.json` |

---

## How Subscriptions Work

ScoutBot reads **two live sources** before every email run:

1. **Google Form responses** — anyone who fills the form is automatically included in the next 7 AM or 7 PM send
2. **Subscribers tab** in the main spreadsheet — for manually managed entries

New sign-ups require zero code changes and zero redeployment. Fill the form → get the next digest.

**Subscription Form:**
👉 [Fill the ScoutBot Subscription Form](https://docs.google.com/spreadsheets/d/1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s/edit?gid=1666713039#gid=1666713039)

**Form Responses Spreadsheet** (what the bot reads automatically):
👉 [https://docs.google.com/spreadsheets/d/1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s/edit?gid=1666713039#gid=1666713039](https://docs.google.com/spreadsheets/d/1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s/edit?gid=1666713039#gid=1666713039)

This spreadsheet is read fresh before every send — so anyone who submits between now and 7 AM (or 7 PM) Lagos will receive that day's digest.
## Privacy

Each subscriber receives a **personally addressed email** — their address appears in the `To:` field and **no one else's**. There is no BCC list and no group header. Subscribers cannot see each other, and the send does not appear as a mass email in the sender's account.

---

## Project Structure

```
ScoutBot/
├── run.py                             # Main entry point
├── notify.py                          # Reads form + subscribers, builds and sends digest
├── cleanup.py                         # Removes closed/expired opportunities
├── requirements.txt                   # Python dependencies with pinned versions
├── .env.example                       # Credentials template (safe to commit)
├── .env                               # Your actual credentials (gitignored)
├── service_account.json               # Google service account key (gitignored)
├── .gitignore
├── scrapy.cfg                         # Scrapy project configuration
├── README.md                          # This file
├── CONTRIBUTING.md                    # How to contribute
├── CODE_REFERENCE.md                  # Every class, function, and variable explained
└── scoutbot/                          # Scrapy project package
    ├── items.py
    ├── pipelines.py
    ├── settings.py
    └── spiders/
        └── opportunities_spider.py
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide.

Want to support the project financially? See the [Fundraising & Support Brief](https://docs.google.com/document/d/1SqxaAg4tvuWp3LgGzqSSSw4_bxBWHmgmrQ9IyyKHtE8/edit) for goals, costs, and account details.

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

## ⚠️ Disclaimer

ScoutBot was vibecoded — built fast, iterated in public, and is genuinely prone to scraping errors, missed deadlines, and the occasional chaos. We do our best to keep it accurate, but always verify opportunities directly at the source before applying.

**Better at coding? Hop on the bot and prove it →** [github.com/TechHub-Extensions/ScoutBot](https://github.com/TechHub-Extensions/ScoutBot)
