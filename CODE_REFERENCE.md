# ScoutBot — Code Reference

This document explains every file, class, function, and variable in the ScoutBot codebase. It is written for people who are new to the project or to Python, so that anyone can understand what is happening and where to make changes.

---

## Technology Stack

Everything in ScoutBot is written in **Python 3.11**. Below is every library and external service used — what role it plays and why it was chosen.

### Core Language

| Technology | Version | Role in ScoutBot |
|-----------|---------|-----------------|
| **Python** | 3.11 | The entire bot is written in Python. Chosen because it has the best ecosystem for scraping, automation, and data work — and it is beginner-accessible. |

### Web Scraping Engine

| Library | Version | Role in ScoutBot |
|---------|---------|-----------------|
| **Scrapy** | 2.15.0 | The heart of the bot. Scrapy is a complete web crawling framework — it visits URLs, downloads pages, extracts data, runs the data through pipelines, and handles rate-limiting and retries automatically. All scraping logic lives inside a Scrapy project. |
| **lxml** | 6.1.0 | A fast HTML/XML parser. Scrapy uses it internally to parse downloaded web pages. You do not interact with this directly. |
| **cssselect** | 1.2.0 | Enables Scrapy to use CSS selectors (e.g. `h2 a::text`) to locate HTML elements. Works behind the scenes when the spider uses `.css()`. |
| **requests** | 2.33.1 | A simple HTTP library used for any direct web requests outside of Scrapy (utility scripts, health checks). |

### Google Sheets Integration

| Library | Version | Role in ScoutBot |
|---------|---------|-----------------|
| **gspread** | 6.2.1 | The main interface for reading and writing to Google Sheets. Used in `SheetsPipeline` to check existing rows and append new opportunities. |
| **google-auth** | 2.49.2 | Google's official library for authenticating with Google services. Handles the service account credentials (the JSON key file) that give ScoutBot access to the spreadsheet. |
| **google-auth-oauthlib** | 1.2.0 | Adds OAuth 2.0 support to google-auth. Required by gspread to authenticate with a service account. |
| **google-auth-httplib2** | 0.2.0 | An HTTP transport layer for Google authentication. Connects the auth library to the API client. |
| **google-api-python-client** | 2.127.0 | Google's official Python client for all Google APIs. Provides the underlying HTTP transport that gspread and google-auth use to communicate with Google Sheets and Drive. |

### Email Sending

| Tool | Version | Role in ScoutBot |
|------|---------|-----------------|
| **smtplib** | Built-in (no install) | Python's standard library for sending emails over SMTP. Used in `notify.py` to connect to Gmail and deliver the digest. |
| **email.mime** | Built-in (no install) | Python's standard library for building email messages — creates the HTML email body and sets headers (From, To, Subject). |
| **Gmail SMTP** | External service | The actual email delivery infrastructure. ScoutBot logs into Gmail's SMTP server (`smtp.gmail.com` on port 465) using an App Password and sends the email from there. Free and reliable. |

### Scheduling

| Library | Version | Role in ScoutBot |
|---------|---------|-----------------|
| **schedule** | 1.2.2 | A lightweight Python library for running functions at set times. Used in `run.py` to trigger the full pipeline at 7:00 AM and 7:00 PM every day. No background process, daemon, or cron needed — just a loop. |

### Configuration & Security

| Library | Version | Role in ScoutBot |
|---------|---------|-----------------|
| **python-dotenv** | 1.2.2 | Reads a `.env` file and loads its contents as environment variables into Python. This is how ScoutBot accesses credentials (email, password, spreadsheet ID) without hardcoding them in source files. |

### External Services (APIs)

| Service | Role in ScoutBot |
|---------|-----------------|
| **Google Sheets API** | The API that lets ScoutBot read from and write to the shared Google Spreadsheet. Enabled in Google Cloud Console. |
| **Google Drive API** | Required alongside the Sheets API for service account access. Without it, authentication fails even if only Sheets is needed. |
| **Google Service Account** | A non-human Google identity (like a robot account) that the bot uses to authenticate without any user needing to log in. Credentials live in `service_account.json`. |
| **Gmail** | The email provider. ScoutBot sends emails from a Gmail account using a 16-character App Password (not the account's real password). |

### Version Control & Collaboration

| Tool | Role in ScoutBot |
|------|-----------------|
| **Git** | Tracks every change to the codebase |
| **GitHub** | Hosts the repository at [TechHub-Extensions/ScoutBot](https://github.com/TechHub-Extensions/ScoutBot) |
| **.gitignore** | Ensures `.env` and `service_account.json` (which contain real credentials) are never committed to GitHub |

---

## File Map

```
ScoutBot/
├── run.py                             ← Start here. This is the main entry point.
├── notify.py                          ← Everything related to sending emails.
├── requirements.txt                   ← List of Python packages the project needs.
├── .env                               ← Your private credentials (never commit this).
├── .env.example                       ← A safe template showing what .env should look like.
├── service_account.json               ← Google credentials (never commit this).
├── scrapy.cfg                         ← Tells Scrapy where the project settings live.
├── setup_cron.py                      ← Optional helper to schedule automatic runs.
├── README.md                          ← Project overview and quick start guide.
├── CONTRIBUTING.md                    ← How to contribute to the project.
├── CODE_REFERENCE.md                  ← This file.
└── scoutbot/                          ← The Scrapy project package.
    ├── __init__.py                    ← Makes this folder a Python package (leave empty).
    ├── items.py                       ← Defines what an "opportunity" looks like as data.
    ├── pipelines.py                   ← Processes scraped items before saving them.
    ├── settings.py                    ← Configuration for the Scrapy engine.
    └── spiders/
        ├── __init__.py                ← Makes this folder a Python package (leave empty).
        └── opportunities_spider.py   ← The spider that actually scrapes websites.
```

---

## `run.py` — The Main Entry Point

This is the file you run. Everything starts here.

### Functions

---

#### `run_spider(spider_name: str)`

Runs a single Scrapy spider by name using a subprocess (a separate terminal command).

```python
run_spider("opportunities")
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `spider_name` | `str` | The name of the spider to run. Currently only `"opportunities"` exists. |

**What it does:** Calls `scrapy crawl opportunities` as a shell command and waits for it to finish. Logs success or failure.

---

#### `run_all_spiders()`

Loops through the `SPIDERS` list and calls `run_spider()` for each one.

```python
SPIDERS = ["opportunities"]  # Add more spider names here as the project grows
```

---

#### `run_notify()`

Imports and calls the `main()` function from `notify.py`. This sends the email digest.

---

#### `full_pipeline()`

The complete end-to-end run:
1. Calls `run_all_spiders()` → scrapes and updates the sheet
2. Calls `run_notify()` → sends the email

This is what runs twice a day on the schedule.

---

#### `run_schedule()`

Sets up the twice-daily schedule using the `schedule` library.

```python
schedule.every().day.at("07:00").do(full_pipeline)   # 7:00 AM
schedule.every().day.at("19:00").do(full_pipeline)   # 7:00 PM
```

Also runs `full_pipeline()` immediately when the script starts, so you don't have to wait until 7AM for the first run.

Enters an infinite loop (`while True`) that checks every 60 seconds whether it is time to run again.

---

#### `main()`

Reads command-line arguments and decides what to run:

| Command | What happens |
|---------|-------------|
| `python run.py` | Runs the full pipeline once |
| `python run.py --scrape` | Only scrapes and updates the sheet |
| `python run.py --notify` | Only sends the email |
| `python run.py --schedule` | Runs on the 7AM/7PM schedule forever |

---

### Module-level variables

| Variable | Value | Description |
|----------|-------|-------------|
| `SCRIPT_DIR` | Current file's directory | Used to build absolute paths |
| `SPIDERS` | `["opportunities"]` | List of spider names to run |

---

## `notify.py` — Email Sending

Handles reading the Google Sheet and sending the HTML email digest.

### Module-level variables (loaded from `.env`)

| Variable | Source | Description |
|----------|--------|-------------|
| `SENDER_EMAIL` | `.env` | Gmail address that sends the emails |
| `GMAIL_APP_PASSWORD` | `.env` | 16-character Gmail App Password (spaces stripped automatically) |
| `SPREADSHEET_ID` | `.env` | The ID portion of the Google Sheets URL |
| `SERVICE_ACCOUNT_JSON` | `.env` | Path to the service account JSON file |
| `RECIPIENT_EMAILS` | `.env` | List of email addresses that receive the digest |
| `SHEET_URL` | Constructed | Full URL to the Google Sheet, used in the email |

---

### Functions

---

#### `_resolve_json_path() → str`

Returns the absolute path to `service_account.json`. Handles both absolute paths and relative paths (relative to the project folder).

---

#### `fetch_recent_opportunities(limit: int = 30) → list[dict]`

Connects to Google Sheets and returns the last `limit` rows as a list of dictionaries.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | `int` | `30` | Maximum number of rows to return |

Returns: A list of row dictionaries, e.g.:
```python
[
  {
    "Title": "Julius Berger Scholarship",
    "Industry": "Engineering",
    "Category": "Scholarship",
    "Application Link": "https://...",
    ...
  }
]
```

Returns an empty list `[]` if the connection fails.

---

#### `build_html(opps: list[dict]) → str`

Takes the list of opportunities and builds a complete HTML email as a string.

- Reverses the list so the newest opportunities appear at the top
- Assigns a colour-coded badge to each category (scholarships = dark blue, internships = green, etc.)
- Returns a full HTML document string ready to send

| Parameter | Type | Description |
|-----------|------|-------------|
| `opps` | `list[dict]` | Opportunities from `fetch_recent_opportunities()` |

---

#### `send_email(opps: list[dict]) → bool`

Sends the HTML email to all recipients in `RECIPIENT_EMAILS`.

- Connects to Gmail's SMTP server over SSL (port 465)
- Logs in using `SENDER_EMAIL` and `GMAIL_APP_PASSWORD`
- Sends the email built by `build_html()`

Returns `True` if sent successfully, `False` if an error occurred.

---

#### `main()`

The entry point when `notify.py` is run directly or called from `run.py`:
1. Calls `fetch_recent_opportunities(limit=30)`
2. If opportunities exist, calls `send_email()`
3. Logs success or failure

---

## `scoutbot/items.py` — Data Structure

Defines what a single "opportunity" looks like as a Python object.

### Class: `OpportunityItem`

This is a Scrapy `Item` — essentially a dictionary with defined fields. Every opportunity the spider finds is stored as one of these.

| Field | Type | Maps to Spreadsheet Column | Description |
|-------|------|---------------------------|-------------|
| `title` | `str` | Title | Name of the opportunity |
| `industry` | `str` | Industry | Tech / Engineering / Law / Finance / Medicine / General |
| `category` | `str` | Category | Scholarship / Fellowship / Internship / Bootcamp / etc. |
| `range` | `str` | Range | National or International |
| `education_level` | `str` | Education Level | Bachelor / Masters / PhD / HND/OND / Any |
| `organization` | `str` | Organization | Awarding body or host organisation |
| `summary` | `str` | Summary | Short description of the opportunity |
| `application_link` | `str` | Application Link | URL to apply |
| `opening_date` | `str` | Opening Date | When applications opened |
| `deadline` | `str` | Deadline | Application deadline |
| `status` | `str` | Status | Open or Closed |

---

## `scoutbot/pipelines.py` — Processing Scraped Items

After the spider finds an item, it goes through pipelines in order. Each pipeline either keeps the item (passes it through) or drops it.

Pipeline order (set in `settings.py`):
1. `DedupePipeline` (priority 100) — runs first
2. `SheetsPipeline` (priority 200) — runs second

---

### Class: `DedupePipeline`

Prevents duplicate items within a single scraping run.

#### Instance variable: `self.seen`
A Python `set` that stores every `application_link` seen so far in the current run.

#### Method: `process_item(item, spider)`

Called automatically by Scrapy for every item.

- If the item's `application_link` is empty or already in `self.seen`, raises `DropItem` (the item is discarded)
- Otherwise adds the link to `self.seen` and returns the item (it continues to the next pipeline)

---

### Class: `SheetsPipeline`

Writes new opportunities to Google Sheets. Checks against what is already in the sheet so nothing is added twice across different runs.

#### Instance variables

| Variable | Description |
|----------|-------------|
| `self.sheet` | The gspread Sheet object. `None` if connection failed. |
| `self.existing_links` | A set of all `Application Link` values already in the sheet |
| `self.new_rows` | A list of rows to be added at the end of the run |

#### Method: `open_spider(spider)`

Called once when the spider starts.
- Connects to Google Sheets using the service account credentials
- Checks if the header row exists; adds it if not
- Loads all existing `Application Link` values into `self.existing_links`

#### Method: `process_item(item, spider)`

Called for every item that passes through `DedupePipeline`.
- If the item's link is already in `self.existing_links`, drops it
- Otherwise formats the item as a row list and adds it to `self.new_rows`

Row order (matches spreadsheet columns exactly):
```python
[title, industry, category, range, education_level, organization, summary, application_link, opening_date, deadline, status]
```

#### Method: `close_spider(spider)`

Called once when the spider finishes.
- If `self.new_rows` is not empty, calls `sheet.append_rows()` to write them all to the sheet in one API call
- Logs how many rows were added

---

### Module-level constants

| Constant | Value | Description |
|----------|-------|-------------|
| `SPREADSHEET_ID` | From `.env` | Google Sheets document ID |
| `SERVICE_ACCOUNT_JSON` | From `.env` | Path to the JSON credentials file |
| `SHEET_HEADERS` | List of column names | The exact header row the sheet should have |
| `LINK_COL_INDEX` | `7` | Zero-based index of "Application Link" in `SHEET_HEADERS` |

---

## `scoutbot/settings.py` — Scrapy Configuration

Controls how the Scrapy engine behaves.

| Setting | Value | What it means |
|---------|-------|---------------|
| `BOT_NAME` | `"ScoutBot"` | The name Scrapy uses to identify itself |
| `ROBOTSTXT_OBEY` | `False` | Does not obey robots.txt — necessary because some sites block scrapers via robots.txt even though the content is public |
| `CONCURRENT_REQUESTS` | `4` | Scrapy sends 4 requests at a time (polite) |
| `DOWNLOAD_DELAY` | `2` | Waits 2 seconds between requests to avoid getting blocked |
| `RANDOMIZE_DOWNLOAD_DELAY` | `True` | Adds random variation to the delay so it looks more human |
| `AUTOTHROTTLE_ENABLED` | `True` | Automatically slows down if a website is responding slowly |
| `ITEM_PIPELINES` | Dict | Specifies which pipelines to use and in what order |
| `LOG_LEVEL` | `"INFO"` | How much detail to log (INFO = key events only) |

---

## `scoutbot/spiders/opportunities_spider.py` — The Spider

This is the heart of ScoutBot. It visits websites and extracts opportunity data.

---

### Module-level constants (keyword lists)

These dictionaries are used to automatically classify each opportunity based on its text content.

#### `INDUSTRY_KEYWORDS`

Maps an industry name to a list of keywords. If any keyword appears in the title or description, that industry is assigned.

```python
INDUSTRY_KEYWORDS = {
    "Tech": ["tech", "software", "coding", "data", "ai", ...],
    "Engineering": ["engineer", "mechanical", "civil", ...],
    "Law": ["law", "legal", "llb", ...],
    "Finance": ["finance", "accounting", "banking", ...],
    "Medicine": ["medicine", "health", "medical", ...],
}
```

Default (if no keyword matches): `"General"`

#### `CATEGORY_MAP`

Maps a keyword to a category name. Checked against the URL and the text.

```python
CATEGORY_MAP = {
    "scholarship": "Scholarship",
    "fellowship": "Fellowship",
    "internship": "Internship",
    "bootcamp": "Bootcamp",
    "apprentice": "Apprenticeship",
    ...
}
```

#### `RANGE_KEYWORDS_INTL`

List of words that indicate an opportunity is international. If any appear in the text, `Range` is set to `"International"`. Otherwise it defaults to `"National"`.

#### `EDU_KEYWORDS`

Maps education level labels to keywords. Used to set `Education Level`.

---

### Module-level helper functions

These are standalone functions (not inside any class) that the spider uses.

#### `infer_industry(text: str) → str`
Scans `text` for industry keywords and returns the matched industry, or `"General"`.

#### `infer_category(url: str, text: str) → str`
Checks the URL and text for category keywords and returns the matched category, or `"Opportunity"`.

#### `infer_range(text: str) → str`
Returns `"International"` or `"National"` based on keywords in `text`.

#### `infer_edu(text: str) → str`
Returns an education level string (`"Bachelor"`, `"Masters"`, `"PhD"`, etc.).

#### `extract_deadline(text: str) → str`
Uses regular expressions to find a date pattern that looks like a deadline. Returns the date as a string, or an empty string if none is found.

Patterns searched (in order):
1. `"deadline: Month DD, YYYY"`
2. `"apply by: Month DD, YYYY"`
3. `"closes: Month DD, YYYY"`
4. `"closing date: Month DD, YYYY"`
5. `"DD Month YYYY"`
6. `"Month DD, YYYY"`

#### `org_from_url(url: str) → str`
Extracts the organisation name from a URL. For example, `"https://www.scholars4dev.com/..."` returns `"Scholars4Dev"`.

---

### Class: `OpportunitiesSpider`

The main spider class. Scrapy reads this and knows how to run it.

#### Class attributes

| Attribute | Value | Description |
|-----------|-------|-------------|
| `name` | `"opportunities"` | The name used to run it: `scrapy crawl opportunities` |
| `start_urls` | List of URLs | The pages Scrapy visits first |
| `MAX_PAGES` | `3` | How many pages of pagination to follow per site |

#### Method: `parse(self, response)`

Called automatically by Scrapy for every page downloaded.

1. Tries to find articles using CSS selectors for common layouts (`article`, `.post`, `.entry`, etc.)
2. For each article found, extracts: title, link, and summary text
3. Passes those through the helper functions to classify industry, category, range, education level, deadline, and organisation
4. Creates an `OpportunityItem` and `yield`s it (sends it to the pipelines)
5. Looks for a "Next page" link and follows it if the current page count is below `MAX_PAGES`

**How CSS selectors work (brief explanation):**
- `response.css("h2 a::text")` — finds all `<a>` tags inside `<h2>` tags and gets their text
- `.get("")` — gets the first result, or `""` if nothing found
- `.getall()` — gets all results as a list

---

## `setup_cron.py` — Automatic Scheduling (Optional)

A utility script that adds a cron job to run ScoutBot automatically every day at 7AM. This is an alternative to running `python run.py --schedule` manually.

### Function: `setup_cron()`

- Reads the current user's crontab (`crontab -l`)
- Checks if a ScoutBot entry already exists
- If not, adds: `0 7 * * * cd /path/to/scoutbot && python run.py`
- Writes the updated crontab back

> Note: Only works on Linux/macOS. On Windows, use Task Scheduler instead.

---

## How Data Flows Through the System

```
Websites
   ↓
OpportunitiesSpider.parse()       ← Visits pages, extracts raw data
   ↓
OpportunityItem                   ← Packages data into a structured object
   ↓
DedupePipeline.process_item()     ← Drops if duplicate link (same run)
   ↓
SheetsPipeline.process_item()     ← Drops if already in Google Sheet
   ↓
SheetsPipeline.close_spider()     ← Writes all new rows to Google Sheet in one call
   ↓
notify.py → fetch_recent_opportunities()  ← Reads latest rows from sheet
   ↓
notify.py → build_html()          ← Builds the HTML email
   ↓
notify.py → send_email()          ← Sends via Gmail SMTP
   ↓
Recipients' inboxes               ← 4 people receive the digest
```

---

## Common Questions

**Q: Where do I add a new website to scrape?**
A: Add the URL to `start_urls` in `scoutbot/spiders/opportunities_spider.py`.

**Q: Where do I add a new email subscriber?**
A: Edit the `RECIPIENT_EMAILS` line in `.env`. No code changes needed.

**Q: How do I add a new category (e.g. "Hackathon")?**
A: Add `"hackathon": "Hackathon"` to the `CATEGORY_MAP` dictionary in `opportunities_spider.py`.

**Q: How do I add a new industry?**
A: Add an entry to `INDUSTRY_KEYWORDS` in `opportunities_spider.py`.

**Q: What does `yield` do in the spider?**
A: Instead of returning a single value and stopping, `yield` passes one item to the pipeline and then continues processing the next item. It is Python's way of producing a stream of results one at a time.

**Q: What is a Scrapy "pipeline"?**
A: A pipeline is a class with a `process_item()` method that Scrapy calls for every scraped item. It can modify the item, keep it, or discard it. Pipelines run in sequence based on their priority number.

**Q: Why does the spider not obey robots.txt?**
A: Many opportunity websites have generic `robots.txt` files that block all bots, even though their content is freely available and the operators do not actively enforce it. ScoutBot still respects the sites by using download delays and throttling.

---

## Glossary

| Term | Meaning |
|------|---------|
| **Spider** | A Python class that Scrapy uses to visit websites and extract data |
| **Item** | A Scrapy object that holds the data for one scraped opportunity |
| **Pipeline** | A class that processes items after scraping (filter, clean, save) |
| **CSS selector** | A way to target specific HTML elements on a page (e.g. `h2 a::text`) |
| **Deduplication** | The process of removing items that have already been seen |
| **SMTP** | The protocol used to send emails (Simple Mail Transfer Protocol) |
| **Service account** | A Google account for programs (not humans) that has access to APIs |
| **gspread** | A Python library that makes it easy to read and write Google Sheets |
| **Scrapy** | The open-source Python web scraping framework ScoutBot uses |
| **dotenv** | A library that reads `.env` files and loads them as environment variables |
| **.env** | A plain text file holding private configuration values like passwords |
| **cron job** | A Linux/macOS way to schedule a command to run at a set time |
| **yield** | A Python keyword that produces values one at a time from a function |
| **`set`** | A Python data structure that holds unique values — used here for fast duplicate checking |
