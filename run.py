"""
ScoutBot main runner.

Usage:
    python run.py              # Full pipeline: scrape → cleanup closed → update sheet → email
    python run.py --scrape     # Only scrape (update sheet, no email)
    python run.py --cleanup    # Only remove closed opportunities from the sheet
    python run.py --notify     # Only send email (no scraping)
    python run.py --schedule   # Run on schedule: full pipeline at 7AM and 7PM daily

The full pipeline order is:
    1. Scrape every source for new opportunities  → adds new rows
    2. Clean closed opportunities                 → removes expired rows
    3. Send email digest                          → sends the live list
"""

import argparse
import logging
import os
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "scoutbot.log")),
    ],
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPIDERS = ["opportunities"]


def run_spider(spider_name):
    logger.info(f"run.py: Starting spider '{spider_name}'...")
    result = subprocess.run(
        ["scrapy", "crawl", spider_name, "--logfile", "scrapy.log"],
        cwd=SCRIPT_DIR,
    )
    if result.returncode != 0:
        logger.error(f"run.py: Spider '{spider_name}' exited with code {result.returncode}")
    else:
        logger.info(f"run.py: Spider '{spider_name}' done.")


def run_all_spiders():
    for spider in SPIDERS:
        run_spider(spider)


def run_cleanup():
    """Remove closed/expired opportunities from the Google Sheet."""
    sys.path.insert(0, SCRIPT_DIR)
    from cleanup import cleanup
    cleanup()


def run_notify(dry_run=False):
    """Read the sheet and email the digest to all subscribers."""
    sys.path.insert(0, SCRIPT_DIR)
    from notify import run_notify as _run_notify
    _run_notify(dry_run=dry_run)


def run_broadcast():
    """
    Call broadcast.py (distribution-bridge) after scraping.
    Reads the opportunities.json written by WhatsAppQueuePipeline and fans out
    to every registered WhatsApp campus group via the Session Manager API.
    Skips silently if broadcast.py is not present or SESSION_API_URL is unset.
    """
    broadcast_script = os.path.join(SCRIPT_DIR, "distribution-bridge", "broadcast.py")
    if not os.path.exists(broadcast_script):
        logger.info("run.py: distribution-bridge/broadcast.py not found — skipping WhatsApp broadcast.")
        return

    session_url = os.getenv("SESSION_API_URL", "").strip()
    if not session_url:
        logger.info("run.py: SESSION_API_URL not set — skipping WhatsApp broadcast.")
        return

    logger.info("run.py: Starting WhatsApp broadcast...")
    result = subprocess.run(
        [sys.executable, broadcast_script, "--source", "json"],
        cwd=os.path.join(SCRIPT_DIR, "distribution-bridge"),
    )
    if result.returncode != 0:
        logger.warning(f"run.py: broadcast.py exited with code {result.returncode} — check distribution-bridge logs.")
    else:
        logger.info("run.py: WhatsApp broadcast complete.")


def full_pipeline():
    logger.info("run.py: === Full pipeline START ===")
    run_all_spiders()
    run_cleanup()
    run_broadcast()
    run_notify(dry_run=False)
    logger.info("run.py: === Full pipeline COMPLETE ===")


def run_schedule():
    import schedule
    import time

    # Always schedule in UTC so the bot fires at 07:00 and 19:00 WAT
    # regardless of the server's local timezone.
    # WAT (West Africa Time) = UTC+1, so:
    #   07:00 WAT = 06:00 UTC
    #   19:00 WAT = 18:00 UTC
    logger.info("run.py: Scheduler started. Will run at 06:00 UTC (07:00 WAT) and 18:00 UTC (19:00 WAT) daily.")
    schedule.every().day.at("06:00").do(full_pipeline)   # 07:00 Nigeria time
    schedule.every().day.at("18:00").do(full_pipeline)   # 19:00 Nigeria time

    # Run immediately on startup so first results appear right away
    full_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="ScoutBot")
    parser.add_argument("--scrape",   action="store_true", help="Only scrape (update sheet, no email)")
    parser.add_argument("--cleanup",  action="store_true", help="Only remove closed opportunities from the sheet")
    parser.add_argument("--notify",   action="store_true", help="Only send email")
    parser.add_argument("--dry-run",  action="store_true", help="Build email_preview.html without sending")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule (7AM + 7PM daily)")
    args = parser.parse_args()

    if args.scrape:
        run_all_spiders()
    elif args.cleanup:
        run_cleanup()
    elif args.notify or args.dry_run:
        run_notify(dry_run=args.dry_run)
    elif args.schedule:
        run_schedule()
    else:
        full_pipeline()


if __name__ == "__main__":
    main()
