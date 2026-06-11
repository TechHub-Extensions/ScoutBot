# ScoutBot — Project Write-Up

*Submitted for: [Hackathon / Competition Name]*
*Category: Education & Human Potential / Entrepreneurship & Job Creation*

---

## Inspiration

Every week, hundreds of scholarships, fellowships, and internships open for Nigerian students on a national and international scale — with only a few being publicised and taken advantage of, and most of them expiring unfound.

I built ScoutBot because close friends and colleagues of mine have missed brilliant opportunities like the Afara Initiative programme, Microsoft internships, and more. Not because they weren't qualified. Because they found out late — days after the deadline, weeks after it was buried in a blog post someone sent or they stumbled on by accident. That was the moment I realised the problem wasn't the opportunities. As we are always told at events, "Africa needs more opportunities" — and we do. But the ones that exist? We are not finding them in time.

Nigeria has over 2 million university students. The average student checks 6–8 different websites, social media groups, and WhatsApp forwards to stay updated. By the time an opportunity surfaces in their feed, it's often already crowded or closed. I wanted to build something that wakes up every morning, does the searching for them, and delivers only the real ones — clean, direct-linked, and pushed to wherever they already are: their inbox, their WhatsApp group, their Telegram feed.

---

## What It Does

ScoutBot is an automated opportunity intelligence system for Nigerian students. It runs every day at 7 AM WAT, completely on its own, with no human in the loop.

Here's what happens in each run:

1. **Scrapes 21+ organisation pages directly** — PTDF, NDDC, NNPC, MTN Foundation, Tony Elumelu Foundation, Commonwealth Scholarships, Chevening, Fulbright, Mastercard Foundation, World Bank, AfDB, African Union, UNDP, UNICEF, British Council, and more. No news aggregators — only the actual source.
2. **Filters by category** — only Scholarship, Fellowship, and Internship items pass through. Startup/VC noise is dropped.
3. **Deduplicates** against the live Google Sheet — items already stored are dropped before anything is written.
4. **Writes to Google Sheets** — surviving items land in a 5-column sheet: Title | Category | Application Link | Deadline | Date Added, split across two tabs: Nigeria 🇳🇬 and International 🌍.
5. **Cleans expired entries** — any entry whose deadline has passed, or that has been in the sheet for more than 23 days, is automatically removed.
6. **Sends a weekly email digest** every Sunday at 10 AM WAT to 500+ subscribers — a clean HTML newsletter with opportunities grouped by region, colour-coded by category, and direct Apply → buttons.
7. **Broadcasts to WhatsApp campus groups** via the distribution bridge — campus leads register their group on the Campus Lead Portal and choose which level of opportunity to receive (Undergraduate, Graduate/PhD, or Both). ScoutBot joins the group and posts automatically.
8. **Posts to a Telegram channel** — every new opportunity is pushed to the ScoutBot Telegram channel in real time.

The result is a fully automated pipeline that turns scattered web noise into a clean, dead-link-free opportunity feed — delivered every day to wherever Nigerian students already are.

---

## How We Built It

The architecture is intentionally simple and cheap. The entire system runs on free tiers.

**Scraping layer — Python + Scrapy**
Scrapy handles concurrent page fetching with rate limiting, retry logic, and duplicate filtering. Each run checks 21 organisation pages simultaneously. Items are filtered in the parse callback before they ever reach a pipeline. Separate parse functions handle different page structures (PTDF, international scholarship pages, RSS feeds for scholars4dev.com).

**AI scoring layer — Google Gemini 2.0 Flash** *(originally active; now preserved as inactive — see Challenges)*
`scoutbot/gemini_scoring.py` is the file that talks to the Gemini API. Each item was serialised into a prompt asking Gemini to rate relevance (1–10) for Nigerian students and generate a 2-sentence blurb. Items scoring below 5 were dropped via Scrapy's `DropItem` exception before reaching Google Sheets. Rate limiting was enforced with a 6-second inter-call sleep and a 3-attempt exponential retry on 429 errors. This layer has since been removed from the active pipeline — see *Challenges* — but the full implementation is preserved in the codebase for future reactivation.

**Storage layer — Google Sheets + gspread**
`SheetsPipeline` writes survivors to a Google Sheet with two tabs: Nigeria and International. Schema migration is automatic — if the bot detects a mismatched column structure, it updates the header row on the next run. `cleanup.py` runs after every scrape and removes expired rows using header-name column lookup (robust to schema changes).

**Delivery layer — three channels**
- **Gmail SMTP**: `notify.py` builds a responsive HTML email, assembles the subscriber list from multiple sources (env variable, Google Sheet Subscribers tab, Google Form responses), deduplicates and validates every address, records bounces, and sends with graceful per-address error handling.
- **WhatsApp distribution bridge**: `distribution-bridge/whatsapp.js` maintains a persistent WhatsApp Web session via `whatsapp-web.js`. `broadcast.py` reads newly added sheet rows and sends formatted messages to each registered campus group, filtered by the level preference set during registration.
- **Telegram**: `telegram_notify.py` pushes new items to a Telegram channel via the Bot API, built by contributor [@tsouk88](https://github.com/tsouk88).

**Campus Lead Portal — React + Vite**
`frontend-handler/` is a single-page web app where campus leads register their WhatsApp group. They paste their group invite link, choose a delivery level (Undergraduate & Internships / Graduate, Masters & PhD / Both), and ScoutBot joins automatically. Built by contributor [@olamidefasogbon](https://github.com/olamidefasogbon).

**Scheduling — GitHub Actions**
The entire system runs on a GitHub Actions cron workflow (`0 6 * * *` = 7 AM WAT). No server, no VPS, no Replit subscription required. The workflow runs as long as the GitHub repo exists — completely free on public repos.

---

## Challenges We Ran Into

**Cloudflare blocking on GitHub Actions IPs**
Major opportunity sites (`opportunitydesk.org`, `afterschoolafrica.com`) return Cloudflare challenge pages when scraped from GitHub Actions Azure datacenter IPs, even with a real browser user agent. The fix was to move entirely to direct organisation pages — the actual PTDF portal, the actual Chevening page — which are not behind Cloudflare and reliably accessible from GitHub Actions.

**Google News redirect URLs**
An earlier version of ScoutBot consumed Google News RSS feeds. Google News RSS items link to `news.google.com/rss/articles/CBMi...` redirect URLs that require JavaScript to resolve to the actual source article. Scrapy doesn't execute JavaScript. Items would land in the sheet pointing at a Google redirect that is functionally useless — clicking it opened Google News, not the application page. The solution was to drop Google News entirely and scrape the source organisations directly.

**Gemini AI — rate limiting, score distribution, and the decision to step back**
The original pipeline included Gemini 2.0 Flash as a scoring and summarisation layer. The intent was strong: let AI filter out press releases, assign relevance scores, and generate 2-sentence blurbs so subscribers could immediately gauge fit. In practice, three problems emerged:

- **Quota exhaustion from test runs.** The free tier gives 1,500 requests/day. Every debugging or development run consumed the same quota as a production run. On days with active development, the production run would hit the cap mid-pipeline, triggering 60-second retry waits that extended total run time from ~2 minutes to 6–8 minutes.

- **Score clustering.** After prompt engineering ("Score 7+ ONLY if explicitly open to Nigerians or Africans broadly"), scores for items that passed the spider's keyword filters clustered between 6 and 8. Almost nothing scored below 5 — meaning the AI rarely dropped anything the spider hadn't already allowed through. The keyword filters were doing ~80% of the quality work; Gemini was providing marginal additional signal at significant latency cost.

- **Blurb quality was inconsistent.** Approximately 60% of generated blurbs were specific and useful ("Fully funded UK postgraduate study for Nigerian citizens — applications close October 31"). The remaining 40% were generic ("This is a great opportunity for students looking to advance their careers"), which would have embarrassed the digest rather than improving it.

The decision was to remove Gemini from the active pipeline and focus on what worked reliably: direct org pages, keyword filters, and deduplication. The Gemini code is preserved in `gemini_scoring.py` and commented out in `settings.py` and `pipelines.py` — fully intact for reactivation whenever a paid tier or better quota situation makes it viable. This was a deliberate trade-off: **functionality and cost-effectiveness over AI complexity.** A bot that runs clean at zero cost every day is more valuable to 500+ subscribers than an AI-enhanced bot that fails 3 days a week because of API limits.

**Subscriber email validation**
Early digests bounced against corporate email servers. A proper validation pipeline was added: format checking with regex, MX record lookup via `dnspython`, a persistent "Bounced" tab in Google Sheets that blocks resends to known bad addresses, and per-address error handling in the SMTP loop so one bad address doesn't abort the whole send.

**Keeping it alive without a paid server**
GitHub Actions free tier gives 2,000 minutes/month for public repos. ScoutBot uses ~5 minutes per daily run × 30 days = ~150 minutes/month. It will run indefinitely at zero cost on any public GitHub repo with the secrets configured.

---

## Accomplishments We're Proud Of

**500+ email subscribers** acquired entirely through organic word-of-mouth across Nigerian student WhatsApp groups — zero paid promotion, zero budget.

**The WhatsApp campus delivery system.** Built from scratch by [@olamidefasogbon](https://github.com/olamidefasogbon) across 30 pull requests: a full distribution bridge that maintains a persistent WhatsApp session, joins campus groups automatically, filters opportunities by academic level, and broadcasts clean-formatted messages. This is not a third-party integration — it is a custom piece of infrastructure built specifically for ScoutBot.

**The Campus Lead Portal.** A live React web app where group admins register their WhatsApp group and choose their opportunity filter preference. No backend complexity — just a registration form that feeds the distribution bridge.

**Telegram delivery.** A third delivery channel built entirely by a community contributor ([@tsouk88](https://github.com/tsouk88)) who joined the project and added it independently.

**Zero-cost infrastructure.** The entire system — scraping, storage, delivery to 500+ people, three separate channels — runs at ₦0/month. GitHub Actions, Gmail SMTP, Google Sheets API. No server. No subscription.

As a student from a middle-class background in a lower-income country: this is the most impressive feat to me. To build is to live. But being unable to afford to keep what you build alive can be a quiet, persistent challenge. The fact that ScoutBot costs nothing to run means it will keep running regardless of what my finances look like next month.

---

## What We Learned

- **Scrapy's async pipeline model** — how `process_item` interacts with `defer.inlineCallbacks` vs `async def`, and why the modern approach matters for Scrapy 2.13+
- **When to leave AI out** — Gemini was the most technically interesting part of the project and the first thing to get cut. The lesson: AI layers add real value when the problem is genuinely ambiguous (e.g. "is this a real opportunity or a press release?"). When keyword filters already solve 80% of that problem, the AI is adding complexity without proportionate value.
- **Prompt engineering for scoring** — before cutting Gemini, the prompt went through six iterations. The phrase *"Score 7+ ONLY if it is explicitly open to Nigerians or Africans broadly"* reduced irrelevant high scores by ~40%. Worth documenting even though the feature is inactive.
- **Building for longevity** — every design decision was made with: *"will this still run correctly in 6 months when I'm not looking at it?"* That led to auto-migration logic, header-name column lookups instead of index constants, the 23-day cleanup cap, and persistent bounce tracking.

---

## What's Next for ScoutBot

- **Finalise the Telegram section in the README** — waiting on the channel link from [@tsouk88](https://github.com/tsouk88)
- **Add the Campus Lead Portal URL** to the README's subscription section
- **Deadline extraction** — automatically parse deadline dates from opportunity pages and add countdown indicators to the weekly digest
- **Reactivate Gemini** if a paid tier or increased free quota becomes available — the infrastructure is there, commented out and ready
- **Category expansion** — the community has asked for bootcamps and exchange programmes alongside scholarships/fellowships/internships
