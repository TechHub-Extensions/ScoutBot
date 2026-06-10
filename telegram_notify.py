"""
ScoutBot — Telegram Digest

Sends the weekly opportunity digest as a text message to a Telegram
channel or group.  Requires two environment variables:

  TELEGRAM_BOT_TOKEN  — from @BotFather
  TELEGRAM_CHAT_ID    — channel/group ID (e.g. -100xxxxxxxxxx)

Added by tsouk88 (PR #42 / #43).
"""

import os
import logging
import requests
from dotenv import load_dotenv
from notify import fetch_recent_from_tab

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

logger = logging.getLogger(__name__)


def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, json={
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "Markdown",
    })
    if not response.ok:
        logger.error(f"Telegram error: {response.status_code} {response.text}")
    else:
        logger.info("Telegram message sent successfully.")


def build_telegram_text(nigeria_opps, intl_opps):
    def format_section(emoji, label, opps):
        if not opps:
            return f"{emoji} *{label}* — No new opportunities this week.\n"
        lines = [f"{emoji} *{label}* — {len(opps)} this week\n"]
        for opp in opps:
            title    = opp.get("Title", "Untitled")
            link     = opp.get("Application Link", "#")
            deadline = opp.get("Deadline", "")
            dl = f"\n  Due: {deadline}" if deadline else ""
            lines.append(f"• {title}\n  Apply: {link}{dl}\n")
            lines.append(f"• [{title}]({link}){dl}\n")
        return "\n".join(lines)

    nigeria_text = format_section("🇳🇬", "Nigeria", nigeria_opps)
    intl_text    = format_section("🌍", "International", intl_opps)
    return f"{nigeria_text}\n---\n{intl_text}"


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
        return

    nigeria_opps = fetch_recent_from_tab("Nigeria",       limit=25)
    intl_opps    = fetch_recent_from_tab("International", limit=25)

    if not nigeria_opps and not intl_opps:
        logger.warning("notify: No recent opportunities. No message sent.")
        return
    text = build_telegram_text(nigeria_opps, intl_opps)
    send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()