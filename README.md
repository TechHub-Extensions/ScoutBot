# ScoutBot

> An open-source Python bot that automatically scrapes the internet for opportunities for Nigerian students — scholarships, fellowships, internships, bootcamps, and more. It updates a shared Google Spreadsheet and emails a **weekly digest** to subscribers every Sunday.

[![GitHub Issues](https://img.shields.io/github/issues/TechHub-Extensions/ScoutBot)](https://github.com/TechHub-Extensions/ScoutBot/issues)
[![GitHub Stars](https://img.shields.io/github/stars/TechHub-Extensions/ScoutBot)](https://github.com/TechHub-Extensions/ScoutBot/stargazes)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![ScoutBot Scrape](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/scoutbot.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/scoutbot.yml)
[![Weekly Digest](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/digest.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/digest.yml)
[![Pytest](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/pytest.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/pytest.yml)

---

## 📬 Subscribe — Free Weekly Digest

ScoutBot emails a curated digest of the **latest** student opportunities every **Sunday at 10AM Lagos time**.

**[→ Fill the ScoutBot Subscription Form](https://docs.google.com/spreadsheets/d/1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s/edit?gid=1666713039#gid=1666713039)**

No app, no login, no fee. Fill the form once and you're on the list.

📋 [View the live opportunity spreadsheet →](https://docs.google.com/spreadsheets/d/1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU/edit)

---

## What ScoutBot Does

- 🔍 **Scrapes 8+ live feeds daily** — Google News RSS (Nigeria + International), YouthHubAfrica
- 🔗 **Direct application links only** — every link is extracted from the article's "Apply Now" button; items with no findable apply link are dropped before entering the sheet
- 📊 **Writes to two separate tabs**: Nigeria 🇳🇬 and International 🌍 — never mixed
- 🤖 **AI quality scoring** — every new item scored 1–10 by Gemini 2.0 Flash; items scoring below 5 are dropped
- 🧹 **Auto-cleans daily** — entries removed when closed, past deadline, or older than 23 days
- 📧 **One email per week** — Sunday digest with only opportunities added in the last 7 days
- 🚫 **Students only** — scholarships, fellowships, internships, bootcamps. No startup/VC content
- ☁️ **Runs entirely on GitHub Actions** — no server, no Replit dependency, works 24/7 independently

---

## How AI Is Used

ScoutBot uses **Google Gemini 2.0 Flash** to score and summarise every scraped opportunity before it enters the sheet.

```
Scrape → DedupePipeline → GeminiPipeline → SheetsPipeline
           (drop known)    (score 1–10)      (write to Nigeria/International tab)
                           (drop < 5)
                           (add AI blurb)
```

**The AI does two things:**
1. **Scores** each opportunity 1–10 for relevance to Nigerian students — items below 5 are dropped silently
2. **Generates a 2-sentence blurb** that appears in the weekly email so subscribers instantly know if an opportunity is for them

**Why Gemini and not GPT-4 or Claude?**
Gemini 2.0 Flash is available on a free API tier with 1,500 requests/day — enough for ScoutBot's daily volume (typically 5–15 new items) with zero cost.

**Full technical documentation:** [`docs/AI_IMPLEMENTATION.md`](./docs/AI_IMPLEMENTATION.md)

---

## Opportunity Lifecycle

```
Day 0:    Opportunity posted on the web
Day 0–3:  Spider picks it up (MAX_POST_AGE_DAYS = 3)
          → follows article to find direct "Apply Now" link
          → Gemini scores it 1–10
          → if score ≥ 5: written to Google Sheet
Day 7:    Included in Sunday weekly email digest
Day 23:   Hard-removed from sheet by cleanup.py (STALE_DAYS = 23)
```

---

## How It Works

```
Every day at 07:00 WAT (GitHub Actions — scoutbot.yml):
  1. scrapy crawl opportunities  →  scrapes RSS feeds → extracts apply links
                                 →  scores each with Gemini → writes to Nigeria / International tab
  2. python run.py --cleanup     →  removes entries older than 23 days or with past deadlines

Every Sunday 10:00 WAT (GitHub Actions — digest.yml):
  3. python run.py --notify      →  sends weekly digest (last 7 days only) to all subscribers

1st of every month 07:30 WAT (GitHub Actions — admin-report.yml):
  4. python admin_report.py      →  sends monthly stats report to project lead
```

---

## Why ScoutBot Exists

Opportunities for Nigerian students are scattered across dozens of websites with no single reliable source. ScoutBot runs quietly in the background, finds new opportunities as they appear, extracts direct application links, scores them with AI, and delivers them straight to people's inboxes — once a week, clean and fresh.

**This is a bot, not a web app.** No dashboard, no login page, no frontend — just an automated Python system that works independently of any platform.

---

## Project Structure

```
ScoutBot/
├── scoutbot/
│   ├── spiders/
│   │   └── opportunities_spider.py  ← All scraping + RSS + apply link extraction
│   ├── pipelines.py                 ← DedupePipeline → GeminiPipeline → SheetsPipeline
│   ├── items.py                     ← Scrapy item definition
│   └── settings.py                  ← Scrapy settings + pipeline order
├── notify.py                        ← Weekly email digest sender
├── cleanup.py                       ← Removes expired sheet entries (23-day cap)
├── admin_report.py                  ← Monthly stats email to project lead
├── welcome.py                       ← Welcome email for new subscribers
├── run.py                           ← CLI entry point
├── requirements.txt
├── .env.example                     ← Copy to .env and fill in credentials
├── docs/
│   ├── AI_IMPLEMENTATION.md         ← Full Gemini AI pipeline documentation
│   └── VOLUNTEER_ROLES.md           ← Step-by-step guide for all volunteer roles
├── .github/
│   └── workflows/
│       ├── scoutbot.yml             ← Daily 07:00 WAT scrape
│       ├── digest.yml               ← Sunday 10:00 WAT weekly email
│       ├── admin-report.yml         ← Monthly 07:30 WAT stats report
│       ├── welcome.yml              ← Monthly welcome email to new subscribers
│       └── pytest.yml               ← CI tests on every push/PR
├── CHANGELOG.md                     ← Full project history
├── CONTRIBUTING.md
├── CODE_REFERENCE.md
└── ENGINEERING.md
```

---

## 🤝 Volunteer — Help Us Grow ScoutBot

ScoutBot is maintained by a small founding team and open-source contributors. Several roles are open to volunteers — no application required to get started.

**[→ Full volunteer guide: docs/VOLUNTEER_ROLES.md](./docs/VOLUNTEER_ROLES.md)**

| Role | Time/week | Skills needed | How to start |
|------|-----------|---------------|--------------|
| **Source Hunter** | 1–3 hrs | Browser, no coding | [Open issue: "volunteer: Source Hunter"](https://github.com/TechHub-Extensions/ScoutBot/issues/new) |
| **Community Ambassador** | 1–2 hrs | Writing, social media | Start immediately — no approval needed |
| **Issue Triager** | 30 min | Basic GitHub | Open an intro issue first |
| **Data Curator** | 1–2 hrs | Google Sheets | Open an intro issue first |
| **Documentation Writer** | 2–4 hrs | Markdown | Open an intro issue first |
| **Source Monitor** | 30 min | Browser + GitHub | [Open issue: "volunteer: Source Monitor"](https://github.com/TechHub-Extensions/ScoutBot/issues/new) |
| **Email Designer** | 2–5 hrs | HTML + CSS | Open an intro issue first |
| **PR Reviewer** | 1–2 hrs | Python | Open an intro issue first |
| **QA Tester** | 2–4 hrs | Python, CLI | Open an intro issue first |
| **Subscriber Support** | 30 min | Gmail | Open an intro issue first |

To apply: open a GitHub issue titled `volunteer: interested in [Role Name]`. Include your name, location, why you want the role, and available hours.

---

## Run Locally

```bash
git clone https://github.com/TechHub-Extensions/ScoutBot.git
cd ScoutBot
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your credentials (see ENGINEERING.md)

python run.py --scrape      # Scrape only (no email)
python run.py --cleanup     # Remove expired entries only
python run.py --notify      # Send digest email only
python run.py --dry-run     # Build email preview without sending (writes email_preview.html)
python admin_report.py      # Send monthly stats report manually
```

### Required `.env` variables

```env
SENDER_EMAIL=your_gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
SPREADSHEET_ID=your_google_sheet_id
FORM_SHEET_ID=your_form_responses_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
RECIPIENT_EMAILS=email1@gmail.com,email2@gmail.com
GEMINI_API_KEY=your_gemini_api_key
```

---

## GitHub Actions Setup (runs independently)

The bot runs entirely on GitHub Actions free tier — no server required. Add these under **Settings → Secrets → Actions**:

| Secret | Description |
|--------|-------------|
| `SENDER_EMAIL` | Gmail address to send from |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your main password) |
| `SPREADSHEET_ID` | ID of the main Google Sheet |
| `FORM_SHEET_ID` | ID of the subscriber form response sheet |
| `RECIPIENT_EMAILS` | Comma-separated fallback recipients |
| `GOOGLE_SERVICE_ACCOUNT_JSON_B64` | Base64-encoded service account JSON |
| `GEMINI_API_KEY` | Google Gemini API key (free at aistudio.google.com) |

Encode your service account: `base64 -i service_account.json | tr -d '\n'`

Once secrets are set, the bot runs on schedule with **no Replit, no VPS, no cron server** required.

---

## 💛 Support ScoutBot

ScoutBot is open source and free for every subscriber. We are Nigerian students building this with zero budget.

**[→ Support on Paystack (₦1,000)](https://paystack.com/pay/scoutbot)**
**[→ Support on Ko-fi (international)](https://ko-fi.com/scoutbot)**

Organisations can sponsor a featured placement in the Sunday digest for **₦5,000/placement** — reaches 500+ students directly. Email [kamsirichard1960@gmail.com](mailto:kamsirichard1960@gmail.com?subject=ScoutBot%20Sponsorship) to enquire.

📄 **[ScoutBot Fundraising Brief (Google Doc)](https://docs.google.com/document/d/1SqxaAg4tvuWp3LgGzqSSSw4_bxBWHmgmrQ9IyyKHtE8/edit)**

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
- 🤝 **Volunteer** — see the [volunteer guide](./docs/VOLUNTEER_ROLES.md) for non-coding roles

**Ready to code?** Start with issues labelled [`good first issue`](https://github.com/TechHub-Extensions/ScoutBot/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide.

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
    <td align="center" width="140">
      <a href="https://github.com/Arnish-val">
        <img src="https://github.com/Arnish-val.png" width="60" style="border-radius:50%" /><br/>
        <b>Arnish-val</b>
      </a><br/>
      2 PRs — CI badges,<br/>pytest workflow
    </td>
  </tr>
</table>

Want to see your face here? [Open a PR](https://github.com/TechHub-Extensions/ScoutBot/pulls) or [pick an issue](https://github.com/TechHub-Extensions/ScoutBot/issues).

---

## License

MIT — see [LICENSE](./LICENSE).
