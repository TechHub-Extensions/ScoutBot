"""
Sets up a cron job to run ScoutBot automatically every day at 7:00 AM.

Usage:
    python setup_cron.py

This will add a cron entry for the current user.
"""

import subprocess
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
CRON_JOB = f"0 7 * * * cd {SCRIPT_DIR} && {PYTHON} run.py >> {SCRIPT_DIR}/scoutbot.log 2>&1"


def setup_cron():
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    if "run.py" in existing:
        print("ScoutBot cron job already exists.")
        return

    new_crontab = existing.rstrip() + "\n" + CRON_JOB + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True)
    if proc.returncode == 0:
        print(f"Cron job added! ScoutBot will run daily at 7:00 AM.")
        print(f"Job: {CRON_JOB}")
    else:
        print("Failed to set cron job. You can add it manually:")
        print(f"  {CRON_JOB}")


if __name__ == "__main__":
    setup_cron()
