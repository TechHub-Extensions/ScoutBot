# ScoutBot — Hackathon Submission Checklist

Use this file to track every item before submitting to Devpost.

---

## ✅ Done (automated — already in repo)

- [x] Public GitHub repo at https://github.com/TechHub-Extensions/ScoutBot
- [x] AI (Gemini 2.0 Flash) scoring every opportunity in production
- [x] Nigeria opportunities → Nigeria tab; International → International tab (separated)
- [x] Daily 07:00 WAT scrape (GitHub Actions `scoutbot.yml`)
- [x] Weekly Sunday 10:00 WAT email digest (`digest.yml`)
- [x] Written narrative (500–1000 words): `docs/NARRATIVE.md`
- [x] Product evidence with verified run logs: `docs/SUBMISSION_EVIDENCE.md`
- [x] Marketing/expense disclosure: `docs/EXPENSES.md`
- [x] AI technical write-up: `docs/AI_IMPLEMENTATION.md`
- [x] Full changelog: `CHANGELOG.md`
- [x] Website live at https://techhub-extensions.github.io/ScoutBot/
- [x] Payment buttons on website (Paystack + Ko-fi links added)
- [x] Sponsorship offer (₦5,000/featured placement) on website

---

## 🔴 CRITICAL — Must Do Before Submitting

### 1. Generate real revenue (BLOCKS Business Viability criterion)

The hackathon requires "real revenue" — even ₦100 counts if it's a real payment.

**Option A — Paystack (fastest, ~15 minutes):**
1. Go to https://dashboard.paystack.com → Products → Payment Pages
2. Create a page: "Support ScoutBot" → Amount: ₦1,000 (or make it flexible)
3. Copy the payment link (e.g. `https://paystack.com/pay/scoutbot`)
4. Update `docs/index.html` — replace `https://paystack.com/pay/scoutbot` with your real link
5. Share the link in your subscriber WhatsApp groups and ask 3–5 people to pay
6. Screenshot the Paystack dashboard after the first payment — this is your revenue evidence

**Option B — Ko-fi (if Paystack not available):**
1. Go to https://ko-fi.com → Create a page
2. Set it up as "Buy me a coffee for ScoutBot"
3. Update `docs/index.html` — replace `https://ko-fi.com/scoutbot` with your real Ko-fi link
4. Share, get at least one payment

**Option C — Sponsorship (₦5,000, higher value):**
1. Email 5 organisations from the Nigerian student opportunity space
2. Offer: featured placement in next Sunday digest for ₦5,000
3. One yes = revenue evidence + a real customer testimonial

**Revenue evidence to save:**
- Paystack dashboard screenshot showing transaction(s)
- Ko-fi dashboard screenshot
- Or a simple P&L: "Received ₦X,000 from Y customers on [date]"

---

### 2. Record the 3-minute video (required submission)

Must demonstrate AI live in production. Suggested structure:
- 0:00–0:30 — Open https://github.com/TechHub-Extensions/ScoutBot/actions, show recent successful daily runs
- 0:30–1:15 — Click into a run, show the Scrapy log: DedupePipeline pre-loading, GeminiPipeline scoring, SheetsPipeline writing to Nigeria/International tabs
- 1:15–2:00 — Open the live Google Sheet: show Nigeria tab + International tab with real data, Date Added + AI Blurb columns
- 2:00–2:30 — Show the weekly email digest: two sections (🇳🇬 + 🌍), AI-generated blurbs under each opportunity
- 2:30–3:00 — Show the website (GitHub Pages), the subscription form, and the subscriber count

Upload to YouTube (unlisted is fine) or directly to Devpost.

---

### 3. Collect customer evidence (3–5 contacts)

The submission requires: "name, email, phone of real customers and testimonials."

Steps:
1. Message 3–5 subscribers you know personally
2. Ask: "Can I include your name, email, and phone as a ScoutBot user for a competition?"
3. Ask them to write 2–3 sentences about how ScoutBot has helped them
4. Save their responses as `docs/CUSTOMER_EVIDENCE.md` (keep private — do not commit to repo)

---

### 4. Share repo with hackathon judges

GitHub requires a username, not an email. Since the repo is **public**, judges can already access it.
On your Devpost submission form, add the repo URL: `https://github.com/TechHub-Extensions/ScoutBot`

If the submission form asks for collaborator access specifically:
- Check if testing@devpost.com has a GitHub account (search on GitHub)
- If yes: go to repo Settings → Collaborators → Add → search their username

---

### 5. Get corporate ID (if available)

- If TechHub Extensions is a registered Nigerian company: provide the CAC registration number
- If not registered: note "Not yet incorporated — sole proprietorship under Kamsi Richard Ivanna"
- Not having one is not a disqualifier ("if available")

---

## 🟡 Should Have Before Submitting

- [ ] `docs/CUSTOMER_EVIDENCE.md` — contact info + testimonials from 3–5 subscribers (keep private)
- [ ] Revenue screenshot saved locally (Paystack/Ko-fi dashboard)
- [ ] Video link ready (YouTube URL or direct upload)

---

## 📋 Submission Form Checklist (Devpost)

When filling the Devpost form:

| Field | What to Enter |
|-------|---------------|
| Project name | ScoutBot |
| Tagline | AI-native opportunity digest for Nigerian students |
| GitHub repo URL | https://github.com/TechHub-Extensions/ScoutBot |
| Demo video | [Your YouTube link] |
| Written narrative | Paste contents of `docs/NARRATIVE.md` |
| Revenue evidence | Upload Paystack/Ko-fi screenshot |
| Marketing spend | ₦0 (paste from `docs/EXPENSES.md`) |
| Product evidence | Link to GitHub Actions + paste from `docs/SUBMISSION_EVIDENCE.md` |
| Customer evidence | Upload separately (not in public repo) |
| Category | Education & Human Potential (primary) |
| Second category | Entrepreneurship & Job Creation |

---

## 📂 All Submission Docs

| Document | Location |
|----------|----------|
| Written narrative | `docs/NARRATIVE.md` |
| Product evidence | `docs/SUBMISSION_EVIDENCE.md` |
| Expense disclosure | `docs/EXPENSES.md` |
| AI technical write-up | `docs/AI_IMPLEMENTATION.md` |
| Changelog | `CHANGELOG.md` |
| Customer evidence | Private — do not commit |
