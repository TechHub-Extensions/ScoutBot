# Changelog

All notable changes to ScoutBot are documented here.  
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [Unreleased]

### Added
- International Google News RSS feeds — Commonwealth, UK, UN, World Bank opportunities now populate the International tab automatically
- `docs/AI_IMPLEMENTATION.md` — full technical write-up of the Gemini AI pipeline
- `CHANGELOG.md` — this file (closes #48)
- GitHub Actions status badges in README (contributed by @Arnish-val, closes #49)
- pytest CI workflow — runs on every push and PR (contributed by @Arnish-val, closes #56)

### Changed
- `MAX_POST_AGE_DAYS` 14 → **3** — only opportunities posted in the last 3 days enter the sheet, keeping content ultra-fresh
- `STALE_DAYS` 33 → **23** — total opportunity lifecycle capped at 23 days (posted → uploaded → removed)
- `GeminiPipeline` model `gemini-1.5-flash` → `gemini-2.0-flash` (1.5 returned 404 for some API keys)
- `DedupePipeline` now pre-loads existing sheet links at spider open so Gemini is never called on items already in the sheet (eliminates wasted API quota)
- Google News RSS routing now uses `forced_range` via Scrapy `meta` — Nigeria feeds always → Nigeria tab; International feeds always → International tab

---

## [1.5.0] — 2026-06-10

### Added
- Google News RSS spider as primary source (4 Nigeria-specific feeds)
- `DedupePipeline` priority 100: drops within-run duplicates and sheet pre-loads before Gemini runs
- `GeminiPipeline` priority 150: AI quality scoring with `threading.Semaphore(1)` + 4 s sleep for ~10 RPM rate limiting

### Fixed
- `afterschoolafrica.com` and `opportunitydesk.org` confirmed Cloudflare-blocking GitHub Actions IPs — removed from `start_urls` permanently
- Gemini model 404: updated to `gemini-2.0-flash`
- All sheet writes were failing silently when worksheet handle was `None` — now raises and logs explicitly

### Removed
- All Cloudflare-blocked source URLs from the spider

---

## [1.4.0] — 2026-06-09

### Added
- `GeminiPipeline` — AI scoring of every opportunity using Google Gemini Flash
  - Score 1–10 for relevance to Nigerian students
  - Auto-drops items scoring below 5
  - Generates a punchy 1–2 sentence blurb for the email digest
- `announce.py` — one-time update announcement email to all 500+ subscribers
- `infer_range()` now URL-aware: items scraped from `/tag/nigeria/` URLs always route to the Nigeria tab regardless of body text

### Changed
- Pipeline order: `DedupePipeline` (100) → `GeminiPipeline` (150) → `SheetsPipeline` (200)
- `listing_url` passed via Scrapy `meta` so `infer_range()` sees the category URL, not the individual post URL

### Fixed
- `infer_range`: removed `"fully funded"` and `"full scholarship"` from `RANGE_KEYWORDS_INTL` — these wrongly routed domestic Nigerian scholarships to the International tab

---

## [1.3.0] — 2026-06 (contributor: @tsouk88)

### Added
- YALI, World Bank, and Commonwealth scholarship sources (#43)
- Telegram bot notification module (`telegram_notify.py`) (#42)
- Auto-label GitHub Actions workflow (#45)
- digest.yml: weekly Sunday digest workflow (separate from daily scrape)

---

## [1.2.0] — 2026-06 (contributor: @saurabhhhcodes, @prajjukorban)

### Added
- Email digest dry-run mode (`--dry-run` flag) (#37)
- Improved mobile email template (#38)
- Improved deadline extraction patterns (#39, #40, #41)

---

## [1.1.0] — 2026-05

### Added
- `WhatsAppInterceptorPipeline` stub (later removed — caused startup crash)
- Multiple new source URLs (pan-African aggregators)
- `infer_range()` function for National/International routing
- Reddit RSS feeds for r/scholarships, r/Internships, r/Nigeria, r/Africa

### Fixed
- `WhatsAppInterceptorPipeline` removed from `ITEM_PIPELINES` — was crashing Scrapy on startup with `ModuleNotFoundError`
- Both original Nigerian sources dead: `scholarshipregion.com` (404) and `myschoolng.com` (DNS failure)

---

## [1.0.0] — 2026-04

### Added
- Initial Scrapy spider scraping scholarships, fellowships, internships
- Google Sheets integration via `gspread` + service account
- `SheetsPipeline` writing to Nigeria and International tabs
- `notify.py` email digest sender (batched, bounce-tracking)
- `cleanup.py` removing expired/stale entries
- `run.py` CLI with `--scrape`, `--notify`, `--cleanup`, `--schedule` flags
- GitHub Actions workflow for daily scraping and weekly digest
- `CONTRIBUTING.md`, `ENGINEERING.md`, `CODE_REFERENCE.md`

---

[Unreleased]: https://github.com/TechHub-Extensions/ScoutBot/compare/main...HEAD
