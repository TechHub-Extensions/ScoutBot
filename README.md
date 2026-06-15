# ScoutBot

> An open-source Python bot that automatically finds scholarships, fellowships, and internships for Nigerian students. It updates a shared Google Spreadsheet, sends a weekly email digest, and delivers opportunities directly to WhatsApp campus groups and a Telegram channel.

[![GitHub Issues](https://img.shields.io/github/issues/TechHub-Extensions/ScoutBot)](https://github.com/TechHub-Extensions/ScoutBot/issues)
[![GitHub Stars](https://img.shields.io/github/stars/TechHub-Extensions/ScoutBot)](https://github.com/TechHub-Extensions/ScoutBot/stargazes)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![ScoutBot Scrape](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/scoutbot.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/scoutbot.yml)
[![Weekly Digest](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/digest.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/digest.yml)
[![Pytest](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/pytest.yml/badge.svg)](https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/pytest.yml)

---

## 📬 Three Ways to Receive ScoutBot

### 1 — Weekly Email Digest (free, no login)

ScoutBot emails a curated digest of the **latest** student opportunities every **Sunday at 10AM Lagos time**.

**[→ Fill the ScoutBot Subscription Form](https://docs.google.com/spreadsheets/d/1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s/edit?gid=1666713039#gid=1666713039)**

No app, no login, no fee. Fill the form once and you're on the list.

---

### 2 — WhatsApp Campus Delivery V2 (filtered by level)

> 🆕 **V2 released June 2026** — graduate-level filtering added, Nigerian timezone accuracy fixed, and portal relaunched at [scout-bott.vercel.app](https://scout-bott.vercel.app).

Campus leads can register their WhatsApp group to receive opportunities **automatically, filtered by academic level**:

| Option | What you receive |
|--------|-----------------|
| **Both** | All opportunities — Undergrad + Graduate/PhD |
| **Undergraduate & Internships only** | Entry-level, NYSC-eligible, and internship posts |
| **Graduate, Masters & PhD only** | Postgraduate scholarships and fellowships |

**How to register your campus group:**
1. Open the **[Campus Lead Portal →](https://scout-bott.vercel.app)** *(link will be updated — see note below)*
2. Paste your WhatsApp group invite link (`chat.whatsapp.com/...`)
3. Select which type of opportunities your group wants to receive
4. ScoutBot joins your group automatically
5. Make **+234 816 449 9922** (ScoutBot) an Admin so it can post



---

### 3 — Telegram Channel

ScoutBot also publishes opportunities to a Telegram channel. No registration required — just join and get notified.

**[→ Join the ScoutBot Telegram Channel](https://t.me/ScoutBotOpportunities)**

You'll receive the same weekly digest of Nigeria 🇳🇬 and International 🌍 opportunities, posted directly to the channel.

---

📋 [View the live opportunity spreadsheet →](https://docs.google.com/spreadsheets/d/1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU/edit)

---

## What ScoutBot Does

- 🔍 **Scrapes 21+ direct org pages daily** — checks PTDF, NDDC, NNPC, MTN Foundation, Tony Elumelu Foundation, Commonwealth Scholarships, Chevening, Fulbright, World Bank, AfDB, AU, UNDP, UNICEF, British Council, and more
- 🔗 **Direct org application links only** — every link goes to the actual organisation's apply page, never a news aggregator or redirect URL
- 📊 **Two separate tabs**: Nigeria 🇳🇬 and International 🌍 — never mixed
- 📱 **WhatsApp campus delivery V2** — campus leads register their group at [scout-bott.vercel.app](https://scout-bott.vercel.app); opportunities arrive filtered by academic level (undergrad / grad / both), times shown in Nigerian timezone
- 📣 **Telegram channel** — real-time posts as new opportunities are discovered
- 🧹 **Auto-cleans daily** — entries removed when closed, past deadline, or older than 23 days
- 📧 **One email per week** — Sunday digest with only opportunities added in the last 7 days, sent to 500+ subscribers
- 🚫 **Students only** — scholarships, fellowships, internships only. No startup/VC content.
- ☁️ **Runs entirely on GitHub Actions** — no server, no Replit dependency, works 24/7 independently

---

## Accomplishments We're Proud Of

- **500+ email subscribers** acquired organically through student WhatsApp groups and word-of-mouth — zero paid promotion
- **WhatsApp campus delivery system V2** — built from scratch by [@olamidefasogbon](https://github.com/olamidefasogbon): a full distribution bridge that joins WhatsApp groups, filters opportunities by academic level (undergrad / grad / both), and broadcasts automatically. V2 adds graduate-level filtering, Nigerian timezone accuracy, and a relaunched portal at [scout-bott.vercel.app](https://scout-bott.vercel.app)
- **Subscriber web portal** with real-time registration, QR code generation, and live ScoutBot status indicator
- **Telegram integration** — built by [@tsouk88](https://github.com/tsouk88), extending delivery to a third channel with zero extra infrastructure
- **Zero cost infrastructure** — entire stack runs free: GitHub Actions, Gmail SMTP, Google Sheets API
- **All links are direct org URLs** — no news.google.com, no redirects; every row in the sheet links to the actual application page

---

## How It Works

```
Every day at 07:00 WAT (GitHub Actions — scoutbot.yml):
  1. scrapy crawl opportunities  →  checks 21+ org pages for open opportunities
                                 →  extracts direct apply URLs
                                 →  deduplicates against existing sheet entries
                                 →  writes to Nigeria / International tab

  2. python run.py --cleanup     →  removes entries older than 23 days or past deadline

Every Sunday 10:00 WAT (GitHub Actions — digest.yml):
  3. python run.py --notify      →  sends weekly email digest (last 7 days) to all subscribers

After each scrape (broadcast_daemon.py):
  4. WhatsApp distribution bridge  →  sends new items to registered campus groups (filtered by level)
  5. Telegram notification         →  posts new items to Telegram channel

1st of every month 07:30 WAT (GitHub Actions — admin-report.yml):
  6. python admin_report.py      →  monthly stats report to project lead
```

---

## Why ScoutBot Exists

Opportunities for Nigerian students are scattered across dozens of websites with no single reliable source. Most are announced on corporate press offices, government portals, or international org pages that students rarely check. ScoutBot checks all of them automatically, every day, and pushes the results to wherever students already are — their WhatsApp group, their Telegram feed, or their inbox once a week.

---

## Project Structure

```
ScoutBot/
├── scoutbot/
│   ├── spiders/
│   │   └── opportunities_spider.py  ← Scrapes 21+ org pages + scholars4dev RSS
│   ├── pipelines.py                 ← DedupePipeline → SheetsPipeline
│   ├── items.py                     ← Scrapy item definition
│   └── settings.py                  ← Scrapy settings + pipeline order
├── distribution-bridge/             ← WhatsApp delivery system (by olamidefasogbon)
│   ├── whatsapp.js                  ← whatsapp-web.js session manager
│   ├── broadcast.py                 ← Sends items to registered campus groups
│   └── broadcast_daemon.py          ← Daemon that queues and delivers broadcasts
├── frontend-handler/                ← Campus Lead Portal (React + Vite)
│   └── src/
│       └── CampusLeadRegistration.jsx  ← Group registration + level filtering UI
├── notify.py                        ← Weekly email digest sender
├── cleanup.py                       ← Removes expired sheet entries (23-day cap)
├── admin_report.py                  ← Monthly stats email to project lead
├── welcome.py                       ← Welcome email for new subscribers
├── run.py                           ← CLI entry point
├── requirements.txt
├── .env.example                     ← Copy to .env and fill in credentials
├── docs/
│   └── VOLUNTEER_ROLES.md           ← Step-by-step guide for all volunteer roles
├── .github/
│   └── workflows/
│       ├── scoutbot.yml             ← Daily 07:00 WAT scrape
│       ├── digest.yml               ← Sunday 10:00 WAT weekly email
│       ├── admin-report.yml         ← Monthly 07:30 WAT stats report
│       ├── welcome.yml              ← Monthly welcome email to new subscribers
│       └── pytest.yml               ← CI tests on every push/PR
├── CHANGELOG.md
├── CONTRIBUTING.md
└── ENGINEERING.md
```

---

## Opportunity Sources

ScoutBot checks **21 organisation pages directly** every day — no news aggregators, no redirects:

| Nigeria | International |
|---------|---------------|
| PTDF (ptdf.gov.ng) | Commonwealth Scholarship |
| NDDC (nddc.gov.ng) | Chevening Scholarship |
| NNPC Group | Fulbright Program |
| Shell/SNEPCo | Mastercard Foundation |
| MTN Foundation | World Bank |
| Tony Elumelu Foundation | African Development Bank |
| Dangote Foundation | African Union |
| Access Bank | UNDP Nigeria |
| YouthHub Africa | UNICEF |
| NDIC (SIWES) | UN Fellowship, British Council NG |

Plus **scholars4dev.com** RSS as a supplementary feed when it has qualifying items.

---

## 🤝 Volunteer — Help Us Grow ScoutBot

ScoutBot is maintained by a small founding team and open-source contributors. Several roles are open to volunteers — no application required.

**[→ Full volunteer guide: docs/VOLUNTEER_ROLES.md](./docs/VOLUNTEER_ROLES.md)**

| Role | Time/week | Skills needed |
|------|-----------|---------------|
| **Source Hunter** | 1–3 hrs | Browser, no coding |
| **Community Ambassador** | 1–2 hrs | Writing, social media |
| **Issue Triager** | 30 min | Basic GitHub |
| **Data Curator** | 1–2 hrs | Google Sheets |
| **Documentation Writer** | 2–4 hrs | Markdown |
| **Email Designer** | 2–5 hrs | HTML + CSS |
| **PR Reviewer** | 1–2 hrs | Python |
| **QA Tester** | 2–4 hrs | Python, CLI |

To apply: open a GitHub issue titled `volunteer: interested in [Role Name]`.

---

## Run Locally

```bash
git clone https://github.com/TechHub-Extensions/ScoutBot.git
cd ScoutBot
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your credentials (see ENGINEERING.md)

python run.py --scrape      # Scrape only
python run.py --cleanup     # Remove expired entries only
python run.py --notify      # Send digest email only
python run.py --dry-run     # Build email preview without sending
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
```

---

## GitHub Actions Setup (runs independently)

Add these secrets under **Settings → Secrets → Actions**:

| Secret | Description |
|--------|-------------|
| `SENDER_EMAIL` | Gmail address to send from |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your main password) |
| `SPREADSHEET_ID` | ID of the main Google Sheet |
| `FORM_SHEET_ID` | ID of the subscriber form response sheet |
| `RECIPIENT_EMAILS` | Comma-separated fallback recipients |
| `GOOGLE_SERVICE_ACCOUNT_JSON_B64` | Base64-encoded service account JSON |

Encode your service account: `base64 -i service_account.json | tr -d '\n'`

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
| Success (Olamide) | successolamide46@gmail.com | Core Team — WhatsApp delivery |

---

## Contributing

**Quick ways to help:**
- ⭐ **Star this repo** (takes 2 seconds)
- 🐛 **[Open an Issue](https://github.com/TechHub-Extensions/ScoutBot/issues)** — report a broken source, a bug, or a feature idea
- 🔀 **Fork and submit a PR** — add sources, fix bugs, improve email design
- 📣 **Share** with Nigerian student WhatsApp groups, Discord servers, Twitter/X
- 🤝 **Volunteer** — see the [volunteer guide](./docs/VOLUNTEER_ROLES.md)

**Ready to code?** Start with issues labelled [`good first issue`](https://github.com/TechHub-Extensions/ScoutBot/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide.

---

## Contributors

Every merged contribution is permanently credited in [CONTRIBUTORS.md](./CONTRIBUTORS.md).

<table>
  <tr>
    <td align="center" width="140">
      <a href="https://github.com/kamsirichard">
        <img src="https://github.com/kamsirichard.png" width="60" style="border-radius:50%" /><br/>
        <b>kamsirichard</b>
      </a><br/>
      Founder — architecture,<br/>scraping, delivery,<br/>182 commits
    </td>
    <td align="center" width="140">
      <a href="https://github.com/olamidefasogbon">
        <img src="https://github.com/olamidefasogbon.png" width="60" style="border-radius:50%" /><br/>
        <b>olamidefasogbon</b>
      </a><br/>
      30 PRs — WhatsApp delivery<br/>engine, Campus Lead Portal,<br/>link validation
    </td>
    <td align="center" width="140">
      <a href="https://github.com/tsouk88">
        <img src="https://github.com/tsouk88.png" width="60" style="border-radius:50%" /><br/>
        <b>tsouk88</b>
      </a><br/>
      Telegram channel,<br/>new sources, auto-label
    </td>
    <td align="center" width="140">
      <a href="https://github.com/Arnish-val">
        <img src="https://github.com/Arnish-val.png" width="60" style="border-radius:50%" /><br/>
        <b>Arnish-val</b>
      </a><br/>
      CI badges,<br/>pytest workflow
    </td>
  </tr>
</table>

Want to see your face here? [Open a PR](https://github.com/TechHub-Extensions/ScoutBot/pulls) or [pick an issue](https://github.com/TechHub-Extensions/ScoutBot/issues).

---

## License

MIT — see [LICENSE](./LICENSE).
