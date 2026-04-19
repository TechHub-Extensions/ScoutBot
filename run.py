"""
ScoutBot main runner.

Usage:
    python run.py              # Full pipeline: scrape → update sheet → email
    python run.py --scrape     # Only scrape (update sheet, no email)
    python run.py --notify     # Only send email (no scraping)
    python run.py --schedule   # Run on schedule: scrape + email at 7AM and 7PM daily
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


def run_notify():
    sys.path.insert(0, SCRIPT_DIR)
    from notify import main as notify_main
    notify_main()


def full_pipeline():
    logger.info("run.py: === Full pipeline START ===")
    run_all_spiders()
    run_notify()
    logger.info("run.py: === Full pipeline COMPLETE ===")


def run_schedule():
    import schedule
    import time

    logger.info("run.py: Scheduler started. Will run at 07:00 and 19:00 daily.")
    schedule.every().day.at("07:00").do(full_pipeline)
    schedule.every().day.at("19:00").do(full_pipeline)

    # Run immediately on startup so first results appear right away
    full_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="ScoutBot")
    parser.add_argument("--scrape", action="store_true", help="Only scrape (update sheet, no email)")
    parser.add_argument("--notify", action="store_true", help="Only send email")
    parser.add_argument("--schedule", action="store_true", help="Run on schedule (7AM + 7PM daily)")
    args = parser.parse_args()

    if args.scrape:
        run_all_spiders()
    elif args.notify:
        run_notify()
    elif args.schedule:
        run_schedule()
    else:
        full_pipeline()


if __name__ == "__main__":
    main()
