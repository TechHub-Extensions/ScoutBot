# Contributing to ScoutBot

Thank you for your interest in contributing to ScoutBot. This is a **controlled open-source project** — meaning contributions are welcome and encouraged, but all changes go through a review process before being merged. The core identity of the project (a clean, automated Python bot — no web app, no frontend) is non-negotiable.

---

## Project Identity — What ScoutBot Is and Is Not

**ScoutBot is a bot.** It runs in the background, scrapes the internet, updates a spreadsheet, and sends emails. That is its job and it does it well.

**ScoutBot will never be:**
- A web application or dashboard
- A mobile app
- Something that requires a user to log in
- A service with a fancy UI

If you want to build something on top of ScoutBot's data (a frontend, a website, a Telegram bot), that is a separate project. ScoutBot itself stays a clean Python bot. Please respect this before contributing.

---

## How the Project Is Organised

| Role | Responsibility |
|------|---------------|
| **Project Lead** | Final say on all merges and direction (Kamsi Richard Ivanna) |
| **Core Team** | Review pull requests, triage issues, test contributions |
| **Contributors** | Add features, fix bugs, improve docs via pull requests |

All major decisions are made by the project lead. Contributors are welcome to propose features via email or GitHub Issues, but the lead has final authority on what gets merged.

---

## Ways to Contribute

You do not need to be a backend developer to contribute. Here is what the project needs:

| Contribution Type | What It Involves |
|------------------|-----------------|
| **Add new sources** | Add a URL to the spider's `start_urls` list |
| **Improve scraping** | Fix broken selectors, improve field extraction accuracy |
| **Add categories/industries** | Extend keyword lists in the spider |
| **Improve the email template** | Edit the HTML in `notify.py` |
| **Write documentation** | Improve README, CONTRIBUTING, or CODE_REFERENCE |
| **Report broken sources** | Open a GitHub Issue with the site name and what's wrong |
| **Add tests** | Write Python tests for pipelines or utilities |

---

## Contact Before Contributing

Before starting significant work, **please email the team first**. This avoids duplicated effort and makes sure your contribution fits the project direction.

**Primary contact:** kamsirichard1960@gmail.com
**Subject line format:** `[ScoutBot] Brief description of what you want to do`

**Core team emails (copy them in for bigger changes):**
- kamsirichard1960@gmail.com
- tegazion7@gmail.com

---

## Step-by-Step Contribution Guide

### Step 1 — Fork and clone the repository

```bash
# Fork the repo on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/ScoutBot.git
cd ScoutBot
```

### Step 2 — Create a feature branch

Never work directly on `main`. Create a branch named after what you are doing:

```bash
git checkout -b add-worldbank-source
# or
git checkout -b fix-deadline-extraction
# or
git checkout -b improve-email-template
```

Branch naming convention: `type/short-description`
Types: `add`, `fix`, `improve`, `docs`, `test`

### Step 3 — Set up your local environment

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your own credentials in .env
```

### Step 4 — Make your changes

Follow the code standards below. Keep changes focused — one pull request per feature or fix.

### Step 5 — Test your changes locally

Before submitting anything, test it:

```bash
# Test scraping (limit to 10 items so it runs fast)
scrapy crawl opportunities -s CLOSESPIDER_ITEMCOUNT=10 -s LOG_LEVEL=INFO

# Test email
python notify.py

# Test full pipeline
python run.py
```

Make sure no errors appear in the output.

### Step 6 — Commit your changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "add: World Bank Open Data as scraping source"
# or
git commit -m "fix: deadline extraction failing on date format 'DD/MM/YYYY'"
# or
git commit -m "docs: add instructions for cron setup on Ubuntu"
```

Commit message format: `type: short description`
Types: `add`, `fix`, `improve`, `docs`, `test`, `refactor`

### Step 7 — Push to your fork

```bash
git push origin your-branch-name
```

### Step 8 — Open a Pull Request

Go to [github.com/TechHub-Extensions/ScoutBot](https://github.com/TechHub-Extensions/ScoutBot) and open a Pull Request from your fork.

In the PR description, include:
- What you changed and why
- What you tested
- Any issues it closes (e.g. `Closes #12`)

A core team member will review it. You may be asked to make changes before it is merged.

---

## How to Add New Scraping Sources

This is the most common contribution and the simplest one.

### Option A — Add a URL to the existing spider (easiest)

Open `scoutbot/spiders/opportunities_spider.py` and add the URL to `start_urls`:

```python
start_urls = [
    # existing URLs...
    "https://new-opportunity-site.com/category/scholarships/",  # Add here
]
```

The existing parser will handle it automatically if the site uses a standard WordPress-style layout (most opportunity sites do).

### Option B — Customise parsing for a specific site

If the site has a unique structure, add a special case inside the `parse` method:

```python
def parse(self, response):
    url = response.url

    if "specificsite.com" in url:
        for article in response.css("div.custom-article-class"):
            item = OpportunityItem()
            item["title"] = article.css("h2.title::text").get("").strip()
            item["application_link"] = article.css("a.apply-btn::attr(href)").get("")
            # ... fill other fields
            yield item
    else:
        # existing generic parser runs for all other sites
        ...
```

### What makes a good source to add?

- The site focuses on African or Nigerian students
- Opportunities are listed as individual articles or posts
- The site is publicly accessible (no login required)
- It is updated regularly

### Good sources to consider adding

- worldbank.org/en/programs
- commonwealthscholarships.ac.uk
- yali.state.gov
- africaportal.org
- fundsforngos.org
- aiesec.org

---

## How to Add Email Recipients

Subscribers are managed in the `.env` file. **No code changes are needed.**

Open `.env` and add the new email to the comma-separated `RECIPIENT_EMAILS` list:

```env
RECIPIENT_EMAILS=kamsirichard1960@gmail.com,tegazion7@gmail.com,newsubscriber@gmail.com
```

If you are a contributor who does not have access to the production `.env`, email the project lead at **kamsirichard1960@gmail.com** with the subject `[ScoutBot] Add email subscriber` and the email address to add.

---

## Code Standards

### Style
- Python 3.10+ compatible code only
- Follow PEP 8 (use 4 spaces for indentation, not tabs)
- Keep functions short and focused — one function, one job
- Use descriptive variable names (`opportunity_link`, not `x` or `temp`)

### Comments
- Write comments for anything that is not immediately obvious
- Use docstrings on all functions and classes
- Do not comment out code and leave it in — delete it

### Secrets and credentials
- **Never commit `.env` or `service_account.json`** — ever
- Never hardcode emails, passwords, API keys, or spreadsheet IDs in source files
- All configuration goes in `.env` and is read via `os.getenv()`

### Dependencies
- Do not add new Python packages without discussing it first
- If a package is needed, add it to `requirements.txt` with a pinned version

---

## What Will NOT Be Merged

- Pull requests that add a web frontend, dashboard, or GUI
- Code that hardcodes credentials
- Untested code (run it locally first)
- Massive PRs that change everything at once — keep changes focused
- Changes that break the existing spreadsheet column format
- Anything that changes the core scheduling from twice-daily without discussion

---

## Reporting Issues

Found a broken source? A bug? A site that is not being scraped correctly?

Open a GitHub Issue at [github.com/TechHub-Extensions/ScoutBot/issues](https://github.com/TechHub-Extensions/ScoutBot/issues) with:

1. **Title:** Short description of the problem
2. **What you expected:** What should have happened
3. **What actually happened:** Include any error messages
4. **Steps to reproduce:** How can someone else see the same problem?

Or email **kamsirichard1960@gmail.com** with subject `[ScoutBot] Bug: short description`.

---

## Code of Conduct

- Be respectful and constructive in all communications
- Assume good intent — contributors are volunteers
- Focus feedback on the code, not the person
- If you disagree with a decision made by the project lead, raise it via email — not in public comments
- This is a Nigerian student project built for Nigerian students. Keep that spirit in everything you contribute.

---

## Questions?

Email: **kamsirichard1960@gmail.com**
Subject: `[ScoutBot] Your question here`

Or reach out to the founder directly:
**Kamsi Richard Ivanna** — [linkedin.com/in/kamsi-richard-024879257](https://www.linkedin.com/in/kamsi-richard-024879257/)
