# ScoutBot

> An open-source Python bot that automatically scrapes the internet for opportunities for Nigerian students — scholarships, fellowships, internships, bootcamps, and more. It updates a shared Google Spreadsheet and emails a **weekly digest** to subscribers every Sunday.

[![GitHub Issues](https://img.shields.io/github/issues/TechHub-Extensions/ScoutBot)](https://github.com/TechHub-Extensions/ScoutBot/issues)
[![GitHub Stars](https://img.shields.io/github/stars/TechHub-Extensions/ScoutBot)](https://github.com/TechHub-Extensions/ScoutBot/stargazers)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![ScoutBot Scrape](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/scoutbot.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/scoutbot.yml)
[![Weekly Sunday Digest](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/digest.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/digest.yml)
[![Welcome Email](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/welcome.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/welcome.yml)
[![Auto Label Issues](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/auto-label.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/auto-label.yml)
[![Thank Contributor](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/thank-contributor.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/thank-contributor.yml)

---

## 📬 Subscribe — Free Weekly Digest

ScoutBot emails a curated digest of the **latest** student opportunities every **Sunday at 10AM Lagos time**.

**[→ Fill the ScoutBot Subscription Form](https://docs.google.com/spreadsheets/d/1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s/edit?gid=1666713039#gid=1666713039)**

No app, no login, no fee. Fill the form once and you're on the list.

📋 [View the live opportunity spreadsheet →](https://docs.google.com/spreadsheets/d/1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU/edit)

---

## What ScoutBot Does

- 🔍 **Scrapes 30+ sources** every 6 hours — aggregators, Nigerian portals, Asia-specific scholarship pages, and Reddit RSS feeds
- 📊 **Writes to two separate tabs**: Nigeria 🇳🇬 and International 🌍 — never mixed
- 🧹 **Auto-cleans the sheet daily** — expired entries removed, nothing stays on the list longer than 3 weeks
- 📧 **Sends one weekly email** every Sunday with only opportunities added in the last 7 days
- 🔗 **Links go directly to application pages** — not blog posts
- 🚫 **Students only** — scholarships, fellowships, internships, bootcamps. No startup/VC/accelerator content

---

## 💛 Support ScoutBot

ScoutBot is open source and free for every user. We are Nigerian students building this with zero budget.

**Fundraising goal:** ₦2,000,000 (~$1,500 USD) for Twitter/X advertising to reach 4,000 Nigerian students.

📄 **[ScoutBot — Fundraising Brief (Google Doc)](https://docs.google.com/document/d/1SqxaAg4tvuWp3LgGzqSSSw4_bxBWHmgmrQ9IyyKHtE8/edit)**

---

## Why ScoutBot Exists

Opportunities for Nigerian students are scattered across dozens of websites with no single reliable source. ScoutBot runs quietly in the background, finds new opportunities as they appear, logs them into a shared spreadsheet, and delivers them straight to people's inboxes — once a week, clean and fresh.

**This is a bot, not a web app.** No dashboard, no login page, no frontend — just an automated Python system that works.

---

## How It Works

```
Every 6 hours:
  1. scrapy crawl opportunities  →  finds new items, writes to Nigeria / International tab
  2. python run.py --cleanup     →  removes entries older than 21 days or with past deadlines

Every Sunday 10AM WAT:
  3. python run.py --notify      →  sends weekly digest (last 7 days only) to all subscribers

Every 1st of month:
  4. python welcome.py           →  sends welcome email to all subscribers
```

---

## Project Structure

```
ScoutBot/
├── scoutbot/
│   ├── spiders/
│   │   └── opportunities_spider.py  ← All scraping logic
│   ├── pipelines.py                 ← Routes items to Nigeria / International tabs
│   ├── items.py                     ← Scrapy item definition
│   └── settings.py                  ← Scrapy settings
├── notify.py                        ← Weekly email digest sender
├── cleanup.py                       ← Removes expired sheet entries
├── welcome.py                       ← Welcome email for new subscribers
├── announce.py                      ← One-time announcement emails
├── run.py                           ← CLI entry point
├── requirements.txt
├── .env.example                     ← Copy to .env and fill in credentials
├── .github/
│   ├── workflows/
│   │   ├── scoutbot.yml             ← Every-6-hours scrape
│   │   ├── digest.yml               ← Sunday weekly email
│   │   └── welcome.yml              ← Monthly welcome email
│   └── ISSUE_TEMPLATE/              ← GitHub issue forms
├── CONTRIBUTING.md
├── CODE_REFERENCE.md
└── ENGINEERING.md
```

---

## Run Locally

```bash
git clone https://github.com/TechHub-Extensions/ScoutBot.git
cd ScoutBot
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your credentials (see below)

# Run once
python run.py

# Or run individual stages
python run.py --scrape     # Scrape only (no email)
python run.py --cleanup    # Remove expired entries only
python run.py --notify     # Send digest email only
python run.py --schedule   # Run on schedule (local cron)
```

### Required `.env` variables

```env
SENDER_EMAIL=your_gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
SPREADSHEET_ID=your_google_sheet_id
FORM_SHEET_ID=your_form_responses_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
RECIPIENT_EMAILS=email1@gmail.com,email2@gmail.com
```

For the Google Service Account JSON, see [ENGINEERING.md](./ENGINEERING.md).

---

## GitHub Actions Setup

The bot runs entirely on GitHub Actions (free tier). Add these repository secrets under **Settings → Secrets → Actions**:

| Secret | Description |
|--------|-------------|
| `SENDER_EMAIL` | Gmail address to send from |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your main password) |
| `SPREADSHEET_ID` | ID of the main Google Sheet |
| `RECIPIENT_EMAILS` | Comma-separated fallback recipients |
| `GOOGLE_SERVICE_ACCOUNT_JSON_B64` | Base64-encoded service account JSON |

To encode the service account: `base64 -i service_account.json | tr -d '\n'`

---

## The Founding Team

| Name | Email | Role |
|------|-------|------|
| **Kamsi Richard Ivanna** | kamsirichard1960@gmail.com | Founder & Project Lead |
| Ibukun Ojo | adeojoibukun28@gmail.com | Core Team |
| Success | successolamide46@gmail.com | Core Team |

---

## Contributing

ScoutBot is open source and welcomes contributions from developers of all skill levels — especially Nigerian students.

**Quick ways to help:**
- ⭐ **Star this repo** (takes 2 seconds)
- 🐛 **[Open an Issue](https://github.com/TechHub-Extensions/ScoutBot/issues)** — report a broken source, a bug, or a feature idea
- 🔀 **Fork and submit a PR** — add sources, fix bugs, improve email design
- 📣 **Share** with Nigerian student WhatsApp groups, Discord servers, Twitter/X

**Ready to code?** Start with issues labelled [`good first issue`](https://github.com/TechHub-Extensions/ScoutBot/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide.

---

---

## Contributors

Every merged contribution is permanently credited in [CONTRIBUTORS.md](./CONTRIBUTORS.md).

<table>
  <tr>
    <td align="center" width="140">
      <a href="https://github.com/olamidefasogbon">
        <img src="https://github.com/olamidefasogbon.png" width="60" style="border-radius:50%" /><br/>
        <b>olamidefasogbon</b>
      </a><br/>
      30 PRs — WhatsApp engine,<br/>V2 frontend, link validation
    </td>
    <td align="center" width="140">
      <a href="https://github.com/saurabhhhcodes">
        <img src="https://github.com/saurabhhhcodes.png" width="60" style="border-radius:50%" /><br/>
        <b>saurabhhhcodes</b>
      </a><br/>
      3 PRs — dry-run, mobile<br/>email, deadline extraction
    </td>
    <td align="center" width="140">
      <a href="https://github.com/tsouk88">
        <img src="https://github.com/tsouk88.png" width="60" style="border-radius:50%" /><br/>
        <b>tsouk88</b>
      </a><br/>
      4 PRs — new sources,<br/>Telegram, auto-label
    </td>
    <td align="center" width="140">
      <a href="https://github.com/prajjukorban">
        <img src="https://github.com/prajjukorban.png" width="60" style="border-radius:50%" /><br/>
        <b>prajjukorban</b>
      </a><br/>
      1 PR — deadline<br/>extraction patterns
    </td>
  </tr>
</table>

Want to see your face here? [Open a PR](https://github.com/TechHub-Extensions/ScoutBot/pulls) or [pick an issue](https://github.com/TechHub-Extensions/ScoutBot/issues).


---

## License

MIT — see [LICENSE](./LICENSE).
