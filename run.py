"""
ScoutBot — run.py
==================

Single entry point for the full pipeline:
  scrape → clean up stale entries → send digest

Schedule: once daily at 12:00 PM Lagos time (WAT = UTC+1)
  → cron runs at 11:00 UTC (GitHub Actions)
  → local schedule runs at 12:00 WAT

Usage:
  python run.py              # full pipeline once, then exit
  python run.py --schedule   # run on schedule (12:00 PM WAT, every day)
  python run.py --scrape     # only scrape + update sheet
  python run.py --notify     # only send email digest
  python run.py --notify --dry-run  # write email_preview.html without SMTP
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [run] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scoutbot.run")

# ── Daily send time (Lagos / WAT) ─────────────────────────────────────────────
SEND_TIME_WAT = "12:00"   # 12:00 PM Lagos time  =  11:00 UTC


# ── Pipeline steps ────────────────────────────────────────────────────────────

def run_scrape():
    """Run the Scrapy spider and push results into the Google Sheet via pipelines."""
    log.info("▶ Scraping opportunities…")
    result = subprocess.run(
        ["scrapy", "crawl", "opportunities"],
        capture_output=False,
    )
    if result.returncode != 0:
        log.error(f"Scrapy exited with code {result.returncode}")
    else:
        log.info("✓ Scrape complete.")


def run_cleanup():
    """Remove past-deadline rows from the sheet."""
    log.info("▶ Cleaning up expired opportunities…")
    try:
        import cleanup
        cleanup.run_cleanup()
        log.info("✓ Cleanup complete.")
    except Exception as exc:
        log.error(f"Cleanup error: {exc}")


def run_notify(dry_run=False):
    """Read fresh subscribers + open opps, then send the digest."""
    if dry_run:
        log.info("▶ Building digest email preview…")
    else:
        log.info("▶ Sending digest emails…")
    try:
        from notify import run_notify as _notify
        _notify(dry_run=dry_run)
        if dry_run:
            log.info("✓ Digest preview written.")
        else:
            log.info("✓ Digest sent.")
    except Exception as exc:
        log.error(f"Notify error: {exc}")


def run_pipeline():
    """Full pipeline: scrape → cleanup → notify."""
    log.info(f"══ ScoutBot pipeline starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ══")
    run_scrape()
    run_cleanup()
    run_notify()
    log.info("══ Pipeline complete. ══")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="ScoutBot runner")
    parser.add_argument(
        "--schedule", action="store_true",
        help=f"Run on daily schedule at {SEND_TIME_WAT} WAT (blocking)"
    )
    parser.add_argument(
        "--scrape", action="store_true",
        help="Only run the scraper (no email)"
    )
    parser.add_argument(
        "--notify", action="store_true",
        help="Only send the email digest (no scrape)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="With --notify, build email_preview.html and print metadata without SMTP"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.scrape:
        run_scrape()
        run_cleanup()

    elif args.notify:
        run_notify(dry_run=args.dry_run)

    elif args.schedule:
        log.info(
            f"ScoutBot scheduled — will run daily at {SEND_TIME_WAT} WAT "
            f"(keep this process running)"
        )
        schedule.every().day.at(SEND_TIME_WAT).do(run_pipeline)

        # Run once immediately so the first send doesn't wait until noon
        log.info("Running pipeline immediately on startup…")
        run_pipeline()

        while True:
            schedule.run_pending()
            time.sleep(30)

    else:
        # Default: run the full pipeline once and exit
        run_pipeline()


if __name__ == "__main__":
    main()
