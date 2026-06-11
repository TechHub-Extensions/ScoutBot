# AI Implementation in ScoutBot

ScoutBot uses **Google Gemini AI** to score every scraped opportunity before it reaches the Google Sheet or the weekly email digest. This document explains the full AI pipeline — what it does, why it was built this way, and how it fits into the broader system.

---

## Why AI?

Before the AI pipeline was added, ScoutBot scraped everything that matched keyword filters — which meant noisy results:

- News articles *about* a scholarship, not the scholarship itself
- Closed opportunities whose HTML page was still live
- Pan-African content that mentioned Nigeria but was not actually for Nigerian students
- Low-effort social media reposts with no real application information

Gemini solves this by acting as a **quality gate**. Every item passes a relevance score before it's accepted.

---

## The AI Pipeline — Step by Step

```
Scrapy Spider
     │
     ▼
DedupePipeline (priority 100)
  • Drops items already in the sheet (pre-loaded at startup)
  • Drops within-run URL duplicates
  • No API calls — fast
     │
     ▼  (only NEW items reach here)
GeminiPipeline (priority 150)
  • Calls Gemini 2.0 Flash REST API
  • Scores 1–10 for Nigerian student relevance
  • Generates a 1–2 sentence blurb
  • Drops score < 5
  • Rate-limited: Semaphore(1) + 4 s sleep ≈ 10 RPM
  • On any API error → item passes through (scrape never silenced)
     │
     ▼  (only scored, quality items reach here)
SheetsPipeline (priority 200)
  • Writes to Nigeria tab or International tab
  • Adds Date Added, AI Blurb columns
```

---

## The Gemini Prompt

```
You help Nigerian university students discover opportunities.

Rate this opportunity 1-10 for relevance to Nigerian students and write
a punchy 1-2 sentence blurb they can act on immediately.
Rate it 7+ ONLY if it is explicitly open to Nigerians or to Africans broadly,
currently accepting applications, and is a genuine scholarship, fellowship,
internship, or training programme.

Title: {title}
Category: {category}
Summary: {summary}
Deadline: {deadline}

Respond in JSON only — no markdown, no code fences:
{"score": <1-10>, "blurb": "<1-2 sentence blurb>"}
```

**Why this prompt structure:**
- Forces structured JSON output (no parsing ambiguity)
- Sets a high bar (7+) for quality to prevent grade inflation
- Includes deadline so Gemini can detect already-closed opportunities
- Temperature 0.3 — factual, not creative

---

## Model Choice: Gemini 2.0 Flash

| Factor | Decision |
|--------|----------|
| Speed | Flash variant — designed for high-throughput classification tasks |
| Cost | Free tier: 1,500 requests/day at 10 RPM |
| Quality | Sufficient for binary relevance scoring and short blurb generation |
| Latency | ~1–2 s per call (acceptable with sequential processing) |

`gemini-1.5-flash` was the original model but returns HTTP 404 for some API key configurations as of June 2026. All calls now use `gemini-2.0-flash`.

---

## Rate Limiting Strategy

The Gemini free tier allows **10 RPM** (requests per minute). Without rate limiting, all 30–40 scraped items would hit the API simultaneously, causing HTTP 429 errors for every call.

**Solution:** A class-level `threading.Semaphore(1)` plus a 4-second sleep inside `GeminiPipeline._call_gemini()`.

```python
class GeminiPipeline:
    _sem = threading.Semaphore(1)   # Only 1 concurrent Gemini call

    def _call_gemini(self, item):
        with self._sem:
            time.sleep(4)           # ~10 RPM — safe for free tier
            return self._call_gemini_inner(item)
```

**Why Semaphore(1) instead of asyncio?**  
Scrapy's `deferToThread` runs the blocking call in a thread pool. A class-level semaphore is the correct primitive to serialize access across threads without changing Scrapy's async architecture.

---

## Deduplication Before AI

A critical optimisation: `DedupePipeline` pre-loads all existing sheet links at spider startup. This means items already in the sheet are **dropped before they ever reach Gemini** — saving API quota on every daily run.

In a typical daily run:
- 30–40 items scraped from RSS feeds
- 25–35 already in the sheet → dropped by `DedupePipeline` with zero API calls
- 5–10 genuinely new items → scored by Gemini

This keeps daily Gemini usage well within the free tier (well under 100 calls/day).

---

## Graceful Degradation

If Gemini is unavailable (API key missing, quota exhausted, network error), items **pass through with an empty blurb**. The scrape is never silenced by an AI outage:

```python
except Exception as exc:
    logger.warning("GeminiPipeline: API error — %s; passing through.", exc)
    item["ai_blurb"] = ""
    return item
```

The `MIN_SCORE` gate is only applied when Gemini responds successfully.

---

## Quality Threshold

Items scoring **below 5 out of 10** are dropped:

```python
if score < self.MIN_SCORE:
    raise DropItem(f"score={score} — {title[:60]}")
```

**What gets a high score (7–10):**
- Nigerian-specific scholarship with clear deadline
- Commonwealth or UK opportunity explicitly open to Nigerian applicants
- Internship at a named Nigerian company with application link

**What gets a low score (1–4):**
- News article *about* a scholarship closing
- Event for professionals only, not students
- Pan-African listing with no explicit Nigerian eligibility

---

## AI Blurb in the Email Digest

Every opportunity in the weekly Sunday email includes the Gemini-generated blurb as a subtitle under the opportunity title:

```
🎓 NNPC–SNEPCo Postgraduate Scholarship 2026
   "Fully funded UK postgraduate study for Nigerian graduates in STEM fields —
    apply by July 31 via the NNPC portal."
   → [Apply Now]
```

This saves the reader from clicking through to understand what an opportunity is — a key UX improvement for a weekly digest serving 500+ subscribers.

---

## Files

| File | Role |
|------|------|
| `scoutbot/pipelines.py` | `GeminiPipeline`, `DedupePipeline`, `SheetsPipeline` |
| `scoutbot/settings.py` | `ITEM_PIPELINES` priority order |
| `scoutbot/spiders/opportunities_spider.py` | Item fields passed to pipelines |
| `.github/workflows/scoutbot.yml` | `GEMINI_API_KEY` injected from GitHub Secret |

---

## Future Improvements

- **Semantic deduplication** (issue #51): detect the same opportunity posted under two different URLs using Gemini embeddings or title similarity
- **Structured extraction**: use Gemini to parse deadline dates and education level from unstructured article text — replacing the current regex-based extractors
- **Feedback loop**: track which opportunities generate subscriber clicks and feed that signal back into the scoring prompt
