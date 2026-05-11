"""
broadcast.py — ScoutBot Distribution Broadcast Engine
======================================================
Post-processing step that reads new opportunities (from a local JSON export 
produced by ScoutBot's pipeline) and fans them out to every registered 
WhatsApp campus group via the Session Manager API.
"""

import os
import sys
import json
import time
import random
import logging
import argparse
import sqlite3
import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("broadcast")

# ── Config ────────────────────────────────────────────────────────────────────
SESSION_API_URL = os.getenv("SESSION_API_URL", "http://localhost:3001")
SPREADSHEET_ID = os.getenv(
    "SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU"
)
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

# Delay range between messages (seconds) — keeps WhatsApp happy
DELAY_MIN = 2
DELAY_MAX = 7

# ── Catchy Headline Logic ─────────────────────────────────────────────────────

HEADLINES = {
    "tech": [
        "🖥️ TECH ALERT — Your Next Big Break Is Here!",
        "⚡ HOT TECH OPPORTUNITY — Don't Sleep On This!",
        "🚀 ENGINEERING YOUR FUTURE — Apply NOW!",
        "💻 CODE YOUR WAY UP — Fresh Tech Opp Dropped!",
        "🔥 TECHIES, LISTEN UP — This One's For You!",
    ],
    "finance": [
        "💰 MONEY MOVES — A Finance Opportunity Just Dropped!",
        "📈 LEVEL UP YOUR FINANCE CAREER — Act Fast!",
        "🏦 BANKING ON YOUR FUTURE — Fresh Finance Opp!",
        "💼 FINANCE ALERT — This Could Change Everything!",
        "📊 YOUR FINTECH ERA STARTS NOW — Apply Today!",
    ],
    "scholarship": [
        "🎓 FREE MONEY ALERT — Scholarship Opportunity!",
        "✈️ STUDY ABROAD LOADING... Scholarship Inside!",
        "🏆 YOUR SCHOLARSHIP ERA IS NOW — Don't Miss This!",
        "💡 FUNDED OPPORTUNITY — Scholars, This Is For You!",
        "🌍 GO GLOBAL — Scholarship Opportunity Just Dropped!",
    ],
    "default": [
        "🔥 FRESH OPPORTUNITY ALERT — Check This Out!",
        "⚡ THIS WEEK'S HOTTEST OPPORTUNITY — Just Dropped!",
        "🚀 OPPORTUNITY KNOCKING — Will You Answer?",
        "🌟 CAREER-CHANGING OPPORTUNITY — Act Before It Closes!",
        "📢 CAMPUS SCOUTS — New Opportunity Available NOW!",
    ],
}

URGENCY_LABELS = {
    "high":   "🔴 URGENT",
    "medium": "🟡 OPEN NOW",
    "low":    "🟢 OPEN",
}


def classify_opportunity(item: dict) -> str:
    """Classify an opportunity into tech / finance / scholarship / default."""
    text = " ".join([
        item.get("title", ""),
        item.get("category", ""),
        item.get("industry", ""),
        item.get("summary", ""),
    ]).lower()

    tech_keywords = {"tech", "software", "engineering", "data", "ai", "developer",
                     "it", "cyber", "cloud", "machine learning", "devops", "backend",
                     "frontend", "fullstack", "product", "ux", "design", "startup"}
    finance_keywords = {"finance", "fintech", "banking", "investment", "trading",
                        "accounting", "economics", "credit", "capital", "fund",
                        "analyst", "consulting", "insurance", "audit", "tax"}
    scholarship_keywords = {"scholarship", "fellowship", "grant", "funded", "bursary",
                            "award", "study abroad", "exchange", "master", "phd",
                            "postgrad", "fully funded", "stipend"}

    if any(k in text for k in scholarship_keywords):
        return "scholarship"
    if any(k in text for k in finance_keywords):
        return "finance"
    if any(k in text for k in tech_keywords):
        return "tech"
    return "default"


def pick_headline(category: str) -> str:
    return random.choice(HEADLINES.get(category, HEADLINES["default"]))


def assess_urgency(item: dict) -> str:
    """Return high / medium / low based on deadline proximity."""
    deadline_str = item.get("deadline", "")
    if not deadline_str:
        return "medium"
    try:
        for fmt in ("%d %B %Y", "%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                deadline = datetime.datetime.strptime(deadline_str.strip(), fmt).date()
                break
            except ValueError:
                continue
        else:
            return "medium"

        days_left = (deadline - datetime.date.today()).days
        if days_left <= 7:
            return "high"
        if days_left <= 30:
            return "medium"
        return "low"
    except Exception:
        return "medium"


def format_message(item: dict) -> str:
    """Build the full WhatsApp message for a single opportunity."""
    category = classify_opportunity(item)
    headline = pick_headline(category)
    urgency_key = assess_urgency(item)
    urgency_label = URGENCY_LABELS[urgency_key]

    title = item.get("title", "Untitled Opportunity").strip()
    organization = item.get("organization", "").strip()
    industry = item.get("industry", "General").strip()
    education = item.get("education_level", "").strip()
    deadline = item.get("deadline", "Not specified").strip()
    summary = (item.get("summary", "") or "")[:300].strip()
    link = item.get("application_link", "#").strip()
    category_label = item.get("category", "Opportunity").strip()

    lines = [
        f"{headline}",
        "",
        f"*{title}*",
        f"🏢 {organization}" if organization else "",
        "",
        f"🏷️ *Category:* {category_label}",
        f"🏭 *Industry:* {industry}",
        f"🎓 *Level:* {education}" if education else "",
        f"⏰ *Deadline:* {deadline}",
        f"📌 *Status:* {urgency_label}",
        "",
        f"📋 *About this opportunity:*",
        summary if summary else "Details available via the link below.",
        "",
        f"🔗 *Apply here:*",
        link,
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🤖 _Powered by ScoutBot — Your Campus Opportunity Radar_",
        "👥 _Share with a friend who needs this!_",
    ]

    return "\n".join(line for line in lines if line is not None)


# ── Data Sources ──────────────────────────────────────────────────────────────

def fetch_from_sheets(limit: int = None) -> list[dict]:
    """Pull recent opportunities directly from the ScoutBot Google Sheet."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        log.error("Missing gspread/google-auth. Run: pip install gspread google-auth")
        sys.exit(1)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # FIX: Use absolute path relative to this script, avoid ScoutBot-main reference
    json_path = SERVICE_ACCOUNT_JSON
    if not os.path.isabs(json_path):
        json_path = os.path.join(Path(__file__).parent, json_path)

    if not os.path.exists(json_path):
        log.warning(f"Service account file not found at {json_path}. Skipping Sheets.")
        return []

    creds = Credentials.from_service_account_file(json_path, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1

    all_values = sheet.get_all_values()
    if len(all_values) < 2:
        log.warning("No data found in spreadsheet.")
        return []

    headers = [h.lower().replace(" ", "_") for h in all_values[0]]
    rows = all_values[1:]
    if limit:
        rows = rows[-limit:]

    items = []
    for row in rows:
        item = dict(zip(headers, row + [""] * max(0, len(headers) - len(row))))
        items.append(item)

    log.info(f"Fetched {len(items)} opportunities from Google Sheets.")
    return items


def fetch_from_json(filepath: str) -> list[dict]:
    """Load opportunities from a JSON file (intercepted data)."""
    # FIX: Handle relative paths for Azure environment
    if not os.path.isabs(filepath):
        filepath = os.path.join(Path(__file__).parent, filepath)

    if not os.path.exists(filepath):
        log.error(f"JSON file not found: {filepath}")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        log.info(f"Loaded {len(data)} opportunities from {filepath}")
        return data
    log.error("JSON file must be a list of opportunity objects.")
    return []


# ── Group Recipients ──────────────────────────────────────────────────────────

def fetch_registered_groups() -> list[dict]:
    """Fetch active groups from the Session Manager API."""
    try:
        import requests
        resp = requests.get(f"{SESSION_API_URL}/groups/export", timeout=5)
        resp.raise_for_status()
        groups = resp.json()
        log.info(f"Retrieved {len(groups)} active groups from Session Manager API.")
        return groups
    except Exception as e:
        log.warning(f"Could not reach Session Manager API ({e}). Trying direct DB read...")

    # Fallback: check multiple possible DB locations
    db_path = Path(__file__).parent / "scoutbot.db"
    if not db_path.exists():
         db_path = Path(__file__).parent.parent / "scoutbot.db"

    if not db_path.exists():
        log.error(f"Database not found. Cannot broadcast.")
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT group_jid, campus_name, group_name FROM campus_groups "
        "WHERE is_active = 1 AND group_jid IS NOT NULL"
    ).fetchall()
    conn.close()
    groups = [dict(r) for r in rows]
    log.info(f"Retrieved {len(groups)} active groups from local database.")
    return groups


# ── WhatsApp Sender ───────────────────────────────────────────────────────────

def send_via_whatsapp_web_js(group_jid: str, message: str) -> bool:
    try:
        import requests
        resp = requests.post(
            f"{SESSION_API_URL}/send",
            json={"group_jid": group_jid, "message": message},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("success", False)
    except Exception as e:
        log.error(f"Failed to send to {group_jid}: {e}")
        return False


# ── Broadcast Loop ────────────────────────────────────────────────────────────

def broadcast(opportunities: list[dict], groups: list[dict], dry_run: bool = False):
    if not opportunities:
        log.warning("No opportunities to broadcast.")
        return

    if not groups:
        log.warning("No registered groups. Nothing to broadcast.")
        return

    total_sends = len(opportunities) * len(groups)
    log.info(
        f"📡 Broadcasting {len(opportunities)} opportunities "
        f"to {len(groups)} groups ({total_sends} total sends)."
    )

    sent = 0
    failed = 0

    for opp in opportunities:
        message = format_message(opp)
        title = opp.get("title", "Untitled")

        log.info(f"📤 Sending: '{title}' → {len(groups)} groups")

        for group in groups:
            jid = group.get("group_jid")
            campus = group.get("campus_name", "Unknown Campus")

            if not jid:
                log.warning(f"  ⚠️  Skipping {campus} — no JID recorded.")
                continue

            if dry_run:
                log.info(f"  [DRY RUN] Would send to {campus} ({jid})")
                sent += 1
                continue

            success = send_via_whatsapp_web_js(jid, message)
            if success:
                log.info(f"  ✅ Sent to {campus}")
                sent += 1
            else:
                log.warning(f"  ❌ Failed for {campus}")
                failed += 1

            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            time.sleep(delay)

        inter_opp_delay = random.uniform(5, 12)
        if not dry_run:
            time.sleep(inter_opp_delay)

    log.info(
        f"\n{'=' * 50}\n"
        f"📊 Broadcast complete.\n"
        f"   ✅ Sent:    {sent}\n"
        f"   ❌ Failed: {failed}\n"
        f"{'=' * 50}"
    )


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ScoutBot Broadcast Engine"
    )
    # FIX: Default source to 'json' to bypass Google Sheets lock
    parser.add_argument(
        "--source",
        choices=["sheets", "json"],
        default="json",
        help="Data source: 'sheets' or 'json' (default: json)",
    )
    # FIX: Default to opportunities.json (the intercepted data)
    parser.add_argument(
        "--file",
        default="opportunities.json",
        help="Path to JSON file",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit opportunities",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print without sending",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview first message and exit",
    )

    args = parser.parse_args()

    # ── Load opportunities ───────────────────────────────────────────────────
    if args.source == "sheets":
        opportunities = fetch_from_sheets(limit=args.limit)
    else:
        opportunities = fetch_from_json(args.file)
        if args.limit and opportunities:
            opportunities = opportunities[-args.limit:]

    if not opportunities:
        log.error("No opportunities loaded. Exiting.")
        sys.exit(1)

    # ── Preview mode ─────────────────────────────────────────────────────────
    if args.preview:
        sample = opportunities[0]
        print("\n" + "═" * 60)
        print(format_message(sample))
        print("═" * 60)
        sys.exit(0)

    # ── Load groups ──────────────────────────────────────────────────────────
    groups = fetch_registered_groups()

    # ── Broadcast ────────────────────────────────────────────────────────────
    broadcast(opportunities, groups, dry_run=args.dry_run)


if __name__ == "__main__":
    main()