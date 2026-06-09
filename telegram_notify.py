import requests
import os
import logging
from notify import fetch_recent_from_tab

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

logger = logging.getLogger(__name__)

def send_telegram_message(token, chat_id, text):
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )
    if not response.ok:
        logger.error(f"Telegram error: {response.status_code} {response.text}")
    else:
        logger.info("Telegram message sent successfully.")

def build_telegram_text(nigeria_opps, intl_opps):
    def format_section(emoji, label, opps):
        if not opps:
            return f"{emoji} {label} — No new opportunities this week.\n"
        lines = [f"{emoji} *{label}* ({len(opps)} this week)\n"]
        for opp in opps:
            title    = opp.get("Title", "Untitled")
            link     = opp.get("Application Link", "#")
            deadline = opp.get("Deadline", "")
            dl = f"\n  Due: {deadline}" if deadline else ""
            lines.append(f"• {title}\n  Apply: {link}{dl}\n")
        return "\n".join(lines)

    nigeria_text = format_section("🇳🇬", "Nigeria", nigeria_opps)
    intl_text    = format_section("🌍", "International", intl_opps)
    return f"{nigeria_text}\n---\n{intl_text}"


def main():
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
    
