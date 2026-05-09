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


def run_notify():
    """Read the sheet and email the digest to all subscribers."""
    sys.path.insert(0, SCRIPT_DIR)
    from notify import main as notify_main
    notify_main()


def full_pipeline():
    logger.info("run.py: === Full pipeline START ===")
    run_all_spiders()
    run_cleanup()
    run_notify()
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
    parser.add_argument("--scrape", action="store_true", help="Only scrape (update sheet, no email)")
    parser.add_argument("--cleanup", action="store_true", help="Only remove closed opportunities from the sheet")
    parser.add_argument("--notify", action="store_true", help="Only send email")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule (7AM + 7PM daily)")
    args = parser.parse_args()

    if args.scrape:
        run_all_spiders()
    elif args.cleanup:
        run_cleanup()
    elif args.notify:
        run_notify()
    elif args.schedule:
        run_schedule()
    else:
        full_pipeline()


if __name__ == "__main__":
    main()
