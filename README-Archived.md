# ScoutBot — Archived Opportunities

This file tracks opportunity listings that have **closed, expired, or are no longer accepting applications**.

Archived entries are kept here for reference and historical record. They are automatically removed from the live [Google Spreadsheet](https://docs.google.com/spreadsheets/d/1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU/edit) after their deadline passes.

---

## How Archiving Works

ScoutBot runs `cleanup.py` every 6 hours. A listing is archived (removed from the live sheet) when:

| Condition | Action |
|-----------|--------|
| `Status == "Closed"` | Removed immediately |
| `Deadline` date has passed | Removed on next cleanup run |
| `Date Added` is > 21 days old and no deadline set | Removed (stale entry rule) |

---

## Browse Active Opportunities

📋 [**View the live opportunity spreadsheet →**](https://docs.google.com/spreadsheets/d/1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU/edit)

The spreadsheet has two tabs:
- **🇳🇬 Nigeria** — opportunities specifically for Nigerians, local programs, Nigerian organisations
- **🌍 International** — international programs open to Nigerian students (study abroad, global fellowships, etc.)

---

## Subscribe for Weekly Alerts

New listings are emailed to subscribers **every Sunday at 10AM Lagos time**.

**[→ Subscribe to ScoutBot (free)](https://docs.google.com/forms/d/e/1FAIpQLSdummy/viewform)**

---

## Found an Opportunity That Should Be Listed?

[Open an issue →](https://github.com/TechHub-Extensions/ScoutBot/issues/new?template=new_source.yml)

Or email **kamsirichard1960@gmail.com** with the subject `[ScoutBot] New Source`.
