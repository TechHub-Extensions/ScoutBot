"""
ScoutBot — One-time apology / update announcement email.

Sent ONCE to all subscribers after the June 2026 quality overhaul.
After sending, the date is written to a "Config" tab in the spreadsheet.
Every future call (including from digest.yml on Sundays) checks that flag
and exits silently if the announcement was already sent.

Usage:
    python announce.py            # Send to all subscribers (skips if already sent)
    python announce.py --test     # Send only to the 4 core team addresses (always sends)
    python announce.py --force    # Ignore the already-sent flag and send anyway
"""

import argparse
import os
import smtplib
import logging
import time
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SENDER_EMAIL       = os.getenv("SENDER_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
SPREADSHEET_ID     = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
FORM_SHEET_ID      = os.getenv("FORM_SHEET_ID", "1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
GITHUB_URL         = "https://github.com/TechHub-Extensions/ScoutBot"
SHEET_URL          = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
FUNDRAISING_DOC    = "https://docs.google.com/document/d/1SqxaAg4tvuWp3LgGzqSSSw4_bxBWHmgmrQ9IyyKHtE8/edit"

_GMAIL_SEARCH = (
    "https://mail.google.com/mail/u/0/#search/"
    "from%3Akamsirichard1960%40gmail.com+subject%3AScoutBot"
)
_UNSUB_MAILTO = (
    f"mailto:{SENDER_EMAIL}"
    "?subject=Unsubscribe%20from%20ScoutBot"
    "&body=Please%20remove%20me%20from%20the%20ScoutBot%20mailing%20list."
)

TEST_EMAILS = [
    "tegazion7@gmail.com",
    "successolamide46@gmail.com",
    "ayanfeoluwaalalade2000@gmail.com",
    "kamsirichard1960@gmail.com",
]

EMAIL_BATCH_SIZE      = int(os.getenv("EMAIL_BATCH_SIZE", "30"))
EMAIL_BATCH_PAUSE_SEC = int(os.getenv("EMAIL_BATCH_PAUSE_SEC", "360"))


def _resolve_json_path():
    p = SERVICE_ACCOUNT_JSON
    if not os.path.isabs(p):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), p)
    return p


def _get_sheet_client():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(
        _resolve_json_path(),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


CONFIG_TAB  = "Config"
CONFIG_KEY  = "announcement_sent"


def _check_already_sent():
    """Returns the date string if the announcement was already sent, else None."""
    try:
        client = _get_sheet_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        try:
            cfg = ss.worksheet(CONFIG_TAB)
        except Exception:
            return None   # Config tab doesn't exist yet → not sent
        keys = cfg.col_values(1)
        vals = cfg.col_values(2)
        for k, v in zip(keys, vals):
            if k.strip().lower() == CONFIG_KEY and v.strip():
                return v.strip()
    except Exception as exc:
        logger.warning(f"announce: Could not read Config tab — {exc}")
    return None


def _mark_as_sent():
    """Write today's date to Config tab so future runs skip sending."""
    try:
        client = _get_sheet_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        try:
            cfg = ss.worksheet(CONFIG_TAB)
        except Exception:
            cfg = ss.add_worksheet(title=CONFIG_TAB, rows=50, cols=2)
            cfg.append_row(["Key", "Value"])
            logger.info("announce: Created Config tab.")
        # Find existing row or append
        keys = cfg.col_values(1)
        for i, k in enumerate(keys, start=1):
            if k.strip().lower() == CONFIG_KEY:
                cfg.update_cell(i, 2, date.today().isoformat())
                logger.info(f"announce: Updated {CONFIG_KEY} = {date.today().isoformat()}")
                return
        cfg.append_row([CONFIG_KEY, date.today().isoformat()])
        logger.info(f"announce: Wrote {CONFIG_KEY} = {date.today().isoformat()}")
    except Exception as exc:
        logger.error(f"announce: Could not write Config tab — {exc}")


def _all_recipients():
    """Collect every subscriber from both sources."""
    emails = []
    try:
        client = _get_sheet_client()
        ws = client.open_by_key(FORM_SHEET_ID).worksheets()[0]
        emails += [v.strip().lower() for v in ws.col_values(4)[1:] if v.strip() and "@" in v]
    except Exception as exc:
        logger.error(f"announce: Form sheet error — {exc}")

    try:
        client = _get_sheet_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        try:
            sub_ws = ss.worksheet("Subscribers")
            emails += [v.strip().lower() for v in sub_ws.col_values(2)[2:] if v.strip() and "@" in v]
        except Exception:
            pass
    except Exception as exc:
        logger.error(f"announce: Subscribers tab error — {exc}")

    seen, result = set(), []
    for e in emails:
        if e and e not in seen:
            seen.add(e)
            result.append(e)
    return result


HTML_BODY = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;color:#1a1a1a;max-width:600px;margin:auto;padding:24px 16px;background:#fff;">

  <div style="border-bottom:3px solid #1a1a2e;padding-bottom:12px;margin-bottom:20px;">
    <h2 style="margin:0;color:#1a1a2e;font-size:20px;">ScoutBot — An Update &amp; An Apology</h2>
    <p style="margin:4px 0 0;color:#888;font-size:13px;">{date.today().strftime("%B %d, %Y")}</p>
  </div>

  <p style="font-size:15px;line-height:1.7;">Hi,</p>

  <p style="font-size:15px;line-height:1.7;">
    We owe you an apology — and we mean it.
  </p>

  <p style="font-size:14px;line-height:1.8;color:#333;">
    Over the past few weeks, many of you wrote in with the same concerns:
  </p>

  <ul style="font-size:14px;line-height:1.9;color:#555;padding-left:20px;">
    <li>Emails were arriving twice a day — overwhelming your inbox</li>
    <li>Opportunities listed were weeks or even months old</li>
    <li>Links opened blog posts, not actual application pages</li>
    <li>Startup and VC content was mixed in with student opportunities</li>
    <li>There was no easy way to unsubscribe or clear old emails</li>
  </ul>

  <p style="font-size:14px;line-height:1.8;color:#333;">
    You were right on every point. ScoutBot was not meeting the standard it promised.
    Here is exactly what we fixed:
  </p>

  <table style="width:100%;border-collapse:collapse;font-size:14px;margin:16px 0;">
    <tr style="background:#f0f7ff;">
      <td style="padding:10px 12px;border:1px solid #dce8f5;">📧 Emails now arrive <strong>once per week</strong> (Sundays only)</td>
    </tr>
    <tr>
      <td style="padding:10px 12px;border:1px solid #dce8f5;">🇳🇬 / 🌍 Nigerian and international opportunities are now in <strong>separate sections</strong> — never mixed</td>
    </tr>
    <tr style="background:#f0f7ff;">
      <td style="padding:10px 12px;border:1px solid #dce8f5;">📅 The digest only shows opportunities <strong>added in the last 7 days</strong> — no stale listings</td>
    </tr>
    <tr>
      <td style="padding:10px 12px;border:1px solid #dce8f5;">🔗 Every link now goes <strong>directly to the company's application page</strong>, not a blog</td>
    </tr>
    <tr style="background:#f0f7ff;">
      <td style="padding:10px 12px;border:1px solid #dce8f5;">❌ Startup, accelerator, and VC content <strong>removed entirely</strong> — students only</td>
    </tr>
    <tr>
      <td style="padding:10px 12px;border:1px solid #dce8f5;">📊 The spreadsheet is cleaned <strong>daily</strong> — expired entries are auto-removed after 3 weeks</td>
    </tr>
    <tr style="background:#f0f7ff;">
      <td style="padding:10px 12px;border:1px solid #dce8f5;">🔕 <strong>One-click unsubscribe</strong> and a Gmail delete-all link appear in every email</td>
    </tr>
    <tr>
      <td style="padding:10px 12px;border:1px solid #dce8f5;">✅ Invalid and bouncing email addresses are <strong>automatically delisted</strong></td>
    </tr>
  </table>

  <p style="font-size:14px;line-height:1.8;">
    ScoutBot is a student-built, open-source project — no budget, no team, just people who care about making
    opportunities accessible to Nigerian students. Your feedback is what drives it forward.
    Thank you for being honest with us.
  </p>

  <p style="font-size:14px;line-height:1.8;">
    <strong>Your next digest arrives this Sunday.</strong>
  </p>

  <p style="font-size:14px;line-height:1.8;">
    — The ScoutBot Team<br>
    <a href="{GITHUB_URL}" style="color:#1a5276;">{GITHUB_URL}</a>
  </p>

  <div style="margin-top:28px;padding-top:12px;border-top:1px solid #eee;font-size:12px;color:#bbb;">
    <a href="{_UNSUB_MAILTO}" style="color:#c0392b;">Unsubscribe</a>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="{_GMAIL_SEARCH}" style="color:#aaa;">🗑 Delete all ScoutBot emails in Gmail</a>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="{SHEET_URL}" style="color:#aaa;">Full spreadsheet</a>
  </div>

</body>
</html>"""


def send_announcement(recipients):
    if not SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        logger.error("announce: SENDER_EMAIL or GMAIL_APP_PASSWORD not set.")
        return False

    subject  = "ScoutBot — We heard you. Here's what we fixed."
    batches  = [recipients[i:i + EMAIL_BATCH_SIZE]
                for i in range(0, len(recipients), EMAIL_BATCH_SIZE)]

    logger.info(f"announce: Sending to {len(recipients)} recipients in {len(batches)} batch(es).")
    successes = 0

    for i, batch in enumerate(batches, start=1):
        ok = 0
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
                for addr in batch:
                    try:
                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = subject
                        msg["From"]    = f"ScoutBot <{SENDER_EMAIL}>"
                        msg["To"]      = addr
                        msg.attach(MIMEText(HTML_BODY, "html"))
                        server.sendmail(SENDER_EMAIL, [addr], msg.as_string())
                        ok += 1
                    except Exception as exc:
                        logger.error(f"announce: Failed {addr}: {exc}")
            successes += ok
            logger.info(f"announce: Batch {i}/{len(batches)} — {ok}/{len(batch)} sent.")
        except Exception as exc:
            logger.error(f"announce: Batch {i} SMTP error — {exc}")

        if i < len(batches):
            logger.info(f"announce: Pausing {EMAIL_BATCH_PAUSE_SEC}s...")
            time.sleep(EMAIL_BATCH_PAUSE_SEC)

    logger.info(f"announce: Done. {successes}/{len(recipients)} delivered.")
    return successes > 0


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true",
                        help="Send only to the 4 core team addresses (always sends, ignores flag)")
    parser.add_argument("--force", action="store_true",
                        help="Ignore the already-sent flag and send to all subscribers anyway")
    args = parser.parse_args()

    if args.test:
        # Test mode always sends — used by humans to preview, never by automated workflows
        logger.info("announce: TEST MODE — sending to 4 core team addresses.")
        send_announcement(TEST_EMAILS)
        return

    # Check the one-time flag before sending to all subscribers
    if not args.force:
        sent_on = _check_already_sent()
        if sent_on:
            logger.info(
                f"announce: Announcement already sent on {sent_on}. Skipping. "
                f"Use --force to override."
            )
            return

    recipients = _all_recipients()
    logger.info(f"announce: LIVE MODE — sending to {len(recipients)} subscribers.")
    success = send_announcement(recipients)

    # Mark as sent so this never fires again automatically
    if success and not args.force:
        _mark_as_sent()


if __name__ == "__main__":
    main()
