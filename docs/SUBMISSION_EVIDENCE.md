# ScoutBot — Product Evidence

*For hackathon submission: agent execution logs, API usage records, pipeline stats.*

---

## Live Production System

- **Live spreadsheet:** https://docs.google.com/spreadsheets/d/1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU/edit
  - Nigeria tab: opportunities for Nigerian students specifically
  - International tab: Commonwealth, UK, UN, World Bank, Africa fellowships
- **GitHub Actions (public run history):** https://github.com/TechHub-Extensions/ScoutBot/actions
- **Website (GitHub Pages):** https://techhub-extensions.github.io/ScoutBot/

---

## AI Pipeline Architecture

```
Scrapy Spider (8 RSS feeds, daily 07:00 WAT)
     │
     ▼
DedupePipeline (priority 100)
  Pre-loads 38–41 existing sheet links at spider startup.
  Drops items already in the sheet — BEFORE Gemini sees them.
  No API calls. Zero quota cost for repeat items.
     │
     ▼  (only NEW items pass here)
GeminiPipeline (priority 150)
  Model: gemini-2.0-flash (REST API)
  Scores 1–10 for Nigerian student relevance.
  Drops score < 5 silently.
  Generates 1-2 sentence subscriber blurb.
  Rate limit: Semaphore(1) + 4s sleep ≈ 10 RPM (free tier safe).
  Graceful fallback: API errors pass item through with empty blurb.
     │
     ▼  (scored, quality items only)
SheetsPipeline (priority 200)
  Routes by item["range"]:
    "National"       → Nigeria tab
    "International"  → International tab
  Writes: Title, Link, Category, Deadline, Date Added, AI Blurb
```

---

## Verified Production Run — 2026-06-11T00:19 UTC

**Run #27315103159** — [View on GitHub Actions](https://github.com/TechHub-Extensions/ScoutBot/actions/runs/27315103159)

```
Pipeline loaded:
  DedupePipeline (100), GeminiPipeline (150), SheetsPipeline (200)

DedupePipeline: 38 existing sheet links pre-loaded (Gemini will skip these).
GeminiPipeline: AI scoring enabled.
SheetsPipeline: 38 existing entries loaded from Nigeria + International tabs.

RSS feeds scraped:
  Google News RSS Nigeria/scholarship:   5 items kept (3-day window)
  Google News RSS Nigeria/fellowship:    3 items kept
  Google News RSS Nigeria/internship:    6 items kept
  Google News RSS Nigeria/training:      1 item kept
  Google News RSS Intl/Commonwealth:     0 items (no new posts)
  Google News RSS Intl/UK+Nigeria:       2 items kept → International tab
  Google News RSS Intl/Africa fellows:   1 item kept → International tab
  Google News RSS Intl/UN+World Bank:    0 items

Gemini API calls: 3 new items scored
  429 rate-limit hit on 3 calls (daily quota depleted by testing — normal production has ~5 calls/day)
  All 3 items passed through gracefully (empty blurb, not dropped)

SheetsPipeline SUMMARY:
  existing=38, nigeria_new=0, intl_new=3, nigeria_written=0, intl_written=3

Cleanup (23-day cap):
  Nigeria: 0 rows removed
  International: 0 rows removed

Total run time: 39 seconds
```

**Sheet state after this run:** 38 Nigeria entries + 3 International entries = **41 total opportunities**

---

## Verified Production Run — 2026-06-11T00:24 UTC

**Run #27315247119** (second run same day — all 18 scraped items already in sheet)

```
DedupePipeline: 41 existing sheet links pre-loaded (Gemini will skip these).

RSS feeds: 18 items scraped, all 18 dropped by DedupePipeline (already in sheet)
Gemini API calls: 0 (dedup ran before Gemini — zero wasted quota)

SheetsPipeline SUMMARY:
  existing=41 loaded, nigeria_new=0, intl_new=0

Total run time: 28 seconds
```

This demonstrates the deduplication-before-AI optimisation working correctly: 41 items pre-loaded, 18 scraped items all recognised as duplicates, zero Gemini calls consumed.

---

## Weekly Email Digest

- **Schedule:** Every Sunday at 10:00 AM WAT (09:00 UTC) via `digest.yml` workflow
- **Content:** Two sections — 🇳🇬 Nigeria (new items in last 7 days) + 🌍 International (new items in last 7 days)
- **Each entry includes:** Title, Application link, AI-generated 2-sentence blurb, Deadline (where extracted)
- **Subscriber management:** Bounced addresses tracked in "Bounced" tab, permanently excluded from future sends
- **Digest workflow:** https://github.com/TechHub-Extensions/ScoutBot/actions/workflows/digest.yml

---

## GitHub Actions Workflow History

All workflows are public and auditable:

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `scoutbot.yml` | Daily 06:00 UTC (07:00 WAT) | Scrape → AI score → write to sheet |
| `digest.yml` | Sundays 09:00 UTC (10:00 WAT) | Send weekly email digest |
| `welcome.yml` | 1st of month | Welcome email to new subscribers |
| `pytest.yml` | Every push/PR | CI test suite |
| `thank-contributor.yml` | On merged PR | Auto-thank contributors |

---

## Gemini API Usage Record

- **API:** Google Gemini Developer API (free tier)
- **Model:** `gemini-2.0-flash`
- **Daily calls in normal production:** 5–15 (one per genuinely new opportunity)
- **Free tier limit:** 1,500 requests/day, 10 RPM
- **Rate limiting implementation:** `threading.Semaphore(1)` + 4-second sleep between calls
- **API key source:** `GEMINI_API_KEY` GitHub repository secret
- **Documentation:** [`docs/AI_IMPLEMENTATION.md`](./AI_IMPLEMENTATION.md)

---

## Source Code References

| Component | File |
|-----------|------|
| Spider + RSS parsing | `scoutbot/spiders/opportunities_spider.py` |
| AI pipeline | `scoutbot/pipelines.py` — `GeminiPipeline` class |
| Dedup pipeline | `scoutbot/pipelines.py` — `DedupePipeline` class |
| Sheet routing | `scoutbot/pipelines.py` — `SheetsPipeline` class |
| Email digest | `notify.py` |
| Cleanup (23-day cap) | `cleanup.py` |
| Daily workflow | `.github/workflows/scoutbot.yml` |
| Weekly digest workflow | `.github/workflows/digest.yml` |
| AI technical docs | `docs/AI_IMPLEMENTATION.md` |
