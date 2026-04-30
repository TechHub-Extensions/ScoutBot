"""
Sends an HTML email digest of the latest opportunities to all recipients.

To stay within Gmail's per-message recipient cap and to avoid being throttled,
recipients are sent in batches with a pause between each batch.

Configurable via environment variables:
    EMAIL_BATCH_SIZE       — recipients per batch (default 30)
    EMAIL_BATCH_PAUSE_SEC  — seconds to wait between batches (default 360 = 6 min)

Each batch uses BCC so subscribers do not see each other's email addresses.
"""

import os
import smtplib
import logging
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

RECIPIENT_EMAILS = [
    e.strip().lower()
    for e in os.getenv(
        "RECIPIENT_EMAILS",
        "tegazion7@gmail.com,successolamide46@gmail.com,ayanfeoluwaalalade2000@gmail.com,kamsirichard1960@gmail.com",
    ).split(",")
    if e.strip() and "@" in e
]
# Remove duplicates while preserving order
_seen = set()
RECIPIENT_EMAILS = [e for e in RECIPIENT_EMAILS if not (e in _seen or _seen.add(e))]

EMAIL_BATCH_SIZE = int(os.getenv("EMAIL_BATCH_SIZE", "30"))
EMAIL_BATCH_PAUSE_SEC = int(os.getenv("EMAIL_BATCH_PAUSE_SEC", "360"))  # 6 minutes

SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"


def _resolve_json_path():
    p = SERVICE_ACCOUNT_JSON
    if not os.path.isabs(p):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), p)
    return p


def fetch_recent_opportunities(limit=30):
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(_resolve_json_path(), scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        rows = sheet.get_all_records()
        return rows[-limit:] if len(rows) > limit else rows
    except Exception as exc:
        logger.error(f"notify: Could not fetch sheet data: {exc}")
        return []


def build_html(opps):
    category_colors = {
        "Scholarship": "#1a5276",
        "Fellowship": "#6c3483",
        "Internship": "#117a65",
        "Bootcamp": "#b7950b",
        "Apprenticeship": "#784212",
        "Conference": "#1f618d",
        "Grant": "#145a32",
        "VC Funding": "#7b241c",
        "Accelerator": "#943126",
        "Incubator": "#a04000",
        "Pitch Competition": "#922b21",
        "Competition": "#922b21",
        "Award": "#7d6608",
        "Opportunity": "#555",
    }

    rows_html = ""
    for opp in reversed(opps):
        link = opp.get("Application Link", "#")
        title = opp.get("Title", "Untitled")
        cat = opp.get("Category", "Opportunity")
        color = category_colors.get(cat, "#555")
        badge = f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{cat}</span>'
        rows_html += f"""
        <tr>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">
            <a href="{link}" style="color:#1a5276;font-weight:600;text-decoration:none;">{title}</a><br>
            {badge}
          </td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">{opp.get('Industry','')}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">{opp.get('Range','')}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">{opp.get('Education Level','')}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;">{opp.get('Organization','')}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #eee;color:#888;">{opp.get('Deadline','')}</td>
        </tr>"""

    return f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;color:#222;max-width:900px;margin:auto;padding:20px;">
  <div style="background:#1a5276;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;">
    <h1 style="margin:0;font-size:22px;">ScoutBot</h1>
    <p style="margin:4px 0 0;font-size:14px;opacity:0.85;">
      Latest Opportunities for Nigerian Students &amp; Founders &mdash; Scholarships, Fellowships, Grants, VC, Accelerators &amp; More
    </p>
  </div>
  <div style="background:#f9f9f9;padding:16px 24px;border:1px solid #ddd;border-top:none;">
    <p style="margin:0 0 12px;">
      Here are the <strong>{len(opps)}</strong> most recent opportunities found by ScoutBot.
      <a href="{SHEET_URL}" style="color:#1a5276;">View the full list on Google Sheets &rarr;</a>
    </p>
    <table style="width:100%;border-collapse:collapse;font-size:13px;background:#fff;">
      <thead>
        <tr style="background:#1a5276;color:#fff;">
          <th style="padding:9px 7px;text-align:left;">Title &amp; Category</th>
          <th style="padding:9px 7px;text-align:left;">Industry</th>
          <th style="padding:9px 7px;text-align:left;">Range</th>
          <th style="padding:9px 7px;text-align:left;">Level</th>
          <th style="padding:9px 7px;text-align:left;">Organization</th>
          <th style="padding:9px 7px;text-align:left;">Deadline</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
  <div style="padding:12px 24px;font-size:11px;color:#aaa;border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px;">
    ScoutBot &mdash; Open Source |
    <a href="https://github.com/TechHub-Extensions/ScoutBot" style="color:#aaa;">GitHub</a>
    &mdash; You receive this because you are subscribed to ScoutBot alerts.
  </div>
</body>
</html>
"""


def _send_one_batch(server, html_body, subject, batch_recipients):
    """Send one email message to a single batch using BCC."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"ScoutBot <{SENDER_EMAIL}>"
    msg["To"] = f"ScoutBot Subscribers <{SENDER_EMAIL}>"  # generic visible "To"
    # BCC keeps each subscriber's address private from everyone else
    msg["Bcc"] = ", ".join(batch_recipients)
    msg.attach(MIMEText(html_body, "html"))

    server.sendmail(SENDER_EMAIL, batch_recipients, msg.as_string())


def send_email(opps):
    """
    Send the digest in batches of EMAIL_BATCH_SIZE, pausing
    EMAIL_BATCH_PAUSE_SEC between batches.
    """
    if not SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        logger.error("notify: SENDER_EMAIL or GMAIL_APP_PASSWORD not set.")
        return False

    if not RECIPIENT_EMAILS:
        logger.warning("notify: No recipients configured.")
        return False

    subject = f"ScoutBot \u2014 {len(opps)} Latest Opportunities for Nigerian Students & Founders"
    html_body = build_html(opps)

    batches = [
        RECIPIENT_EMAILS[i : i + EMAIL_BATCH_SIZE]
        for i in range(0, len(RECIPIENT_EMAILS), EMAIL_BATCH_SIZE)
    ]
    total_batches = len(batches)
    logger.info(
        f"notify: Sending to {len(RECIPIENT_EMAILS)} recipients in "
        f"{total_batches} batches of up to {EMAIL_BATCH_SIZE} "
        f"(pause {EMAIL_BATCH_PAUSE_SEC}s = {EMAIL_BATCH_PAUSE_SEC // 60} min between batches)."
    )

    successes = 0
    for i, batch in enumerate(batches, start=1):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
                _send_one_batch(server, html_body, subject, batch)
            successes += len(batch)
            logger.info(
                f"notify: Batch {i}/{total_batches} sent successfully "
                f"({len(batch)} recipients)."
            )
        except Exception as exc:
            logger.error(f"notify: Batch {i}/{total_batches} failed — {exc}")

        # Pause between batches (but not after the last one)
        if i < total_batches:
            logger.info(
                f"notify: Pausing {EMAIL_BATCH_PAUSE_SEC}s before batch {i + 1}..."
            )
            time.sleep(EMAIL_BATCH_PAUSE_SEC)

    logger.info(
        f"notify: Done. {successes}/{len(RECIPIENT_EMAILS)} recipients reached."
    )
    return successes > 0


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("notify: Fetching recent opportunities...")
    opps = fetch_recent_opportunities(limit=30)
    if not opps:
        logger.warning("notify: Sheet empty or unreachable. No email sent.")
        return
    send_email(opps)


if __name__ == "__main__":
    main()
