"""
ScoutBot — Email Digest Notifier

Recipient sources (merged & deduplicated each run):
  1. Google Form responses spreadsheet (column D = Email)
  2. "Subscribers" tab in the main spreadsheet (column B = Email)
  3. RECIPIENT_EMAILS environment variable (comma-separated fallback)

Privacy model:
  Each subscriber receives their OWN individual email where they are the only
  visible recipient. No BCC lists, no group headers — nobody can see anyone
  else's address, and it doesn't appear in the sender's Sent folder as a mass
  send. SMTP connections are pooled into batches of EMAIL_BATCH_SIZE (default 30)
  to respect Gmail's rate limits, with EMAIL_BATCH_PAUSE_SEC (default 360s / 6 min)
  between batches.
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

SENDER_EMAIL         = os.getenv("SENDER_EMAIL", "")
GMAIL_APP_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID",
                           "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
FORM_SHEET_ID        = os.getenv("FORM_SHEET_ID",
                           "1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

_ENV_EMAILS = [
    e.strip().lower()
    for e in os.getenv(
        "RECIPIENT_EMAILS",
        "tegazion7@gmail.com,successolamide46@gmail.com,"
        "ayanfeoluwaalalade2000@gmail.com,kamsirichard1960@gmail.com",
    ).split(",")
    if e.strip() and "@" in e
]

EMAIL_BATCH_SIZE      = int(os.getenv("EMAIL_BATCH_SIZE", "30"))
EMAIL_BATCH_PAUSE_SEC = int(os.getenv("EMAIL_BATCH_PAUSE_SEC", "360"))  # 6 minutes

SHEET_URL       = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
FUNDRAISING_DOC = ("https://docs.google.com/document/d/"
                   "1SqxaAg4tvuWp3LgGzqSSSw4_bxBWHmgmrQ9IyyKHtE8/edit")
GITHUB_URL      = "https://github.com/TechHub-Extensions/ScoutBot"


def _resolve_json_path():
    p = SERVICE_ACCOUNT_JSON
    if not os.path.isabs(p):
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), p)
    return p


def _get_sheet_client():
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(_resolve_json_path(), scopes=scopes)
    return gspread.authorize(creds)


def fetch_form_subscribers():
    """
    Read emails from the Google Form responses spreadsheet.
    Emails are in column D (index 4), row 2 onwards (row 1 is the header).
    Returns a deduplicated list of lowercase email strings.
    """
    try:
        client = _get_sheet_client()
        ss = client.open_by_key(FORM_SHEET_ID)
        ws = ss.worksheets()[0]          # first sheet = form responses
        all_values = ws.col_values(4)    # column D (1-indexed)
        emails = [
            v.strip().lower()
            for v in all_values[1:]      # skip header row
            if v.strip() and "@" in v
        ]
        logger.info(f"notify: {len(emails)} emails from Google Form responses.")
        return emails
    except Exception as exc:
        logger.error(f"notify: Could not read Form responses sheet: {exc}")
        return []


def fetch_subscribers_tab():
    """
    Read emails from the 'Subscribers' tab in the main spreadsheet (column B).
    Rows 1 and 2 are header / note — skip them.
    """
    try:
        client = _get_sheet_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        try:
            sub_sheet = ss.worksheet("Subscribers")
        except Exception:
            logger.warning("notify: No 'Subscribers' tab found — skipping.")
            return []
        all_values = sub_sheet.col_values(2)   # column B
        emails = [
            v.strip().lower()
            for v in all_values[2:]             # skip rows 1 and 2
            if v.strip() and "@" in v
        ]
        logger.info(f"notify: {len(emails)} emails from Subscribers tab.")
        return emails
    except Exception as exc:
        logger.error(f"notify: Could not read Subscribers tab: {exc}")
        return []


def build_recipient_list():
    """
    Merge Form responses + Subscribers tab + env variable list.
    Deduplicate while preserving order. Form responses come first so
    anyone who just signed up is always included in the next run.
    """
    combined = fetch_form_subscribers() + fetch_subscribers_tab() + _ENV_EMAILS
    seen, result = set(), []
    for e in combined:
        if e and e not in seen:
            seen.add(e)
            result.append(e)
    logger.info(f"notify: Total unique recipients: {len(result)}")
    return result


def fetch_recent_opportunities(limit=30):
    try:
        client = _get_sheet_client()
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        rows = sheet.get_all_records()
        return rows[-limit:] if len(rows) > limit else rows
    except Exception as exc:
        logger.error(f"notify: Could not fetch sheet data: {exc}")
        return []


def build_html(opps):
    category_colors = {
        "Scholarship":      "#1a5276",
        "Fellowship":       "#6c3483",
        "Internship":       "#117a65",
        "Bootcamp":         "#b7950b",
        "Apprenticeship":   "#784212",
        "Conference":       "#1f618d",
        "Grant":            "#145a32",
        "VC Funding":       "#7b241c",
        "Accelerator":      "#943126",
        "Incubator":        "#a04000",
        "Pitch Competition":"#922b21",
        "Competition":      "#922b21",
        "Award":            "#7d6608",
        "Opportunity":      "#555",
    }

    rows_html = ""
    for opp in reversed(opps):
        link  = opp.get("Application Link", "#")
        title = opp.get("Title", "Untitled")
        cat   = opp.get("Category", "Opportunity")
        color = category_colors.get(cat, "#555")
        badge = (
            f'<span style="background:{color};color:#fff;'
            f'padding:2px 8px;border-radius:4px;font-size:11px;">{cat}</span>'
        )
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
      Latest Opportunities for Nigerian Students &amp; Founders &mdash;
      Scholarships, Fellowships, Grants, VC, Accelerators &amp; More
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

  <div style="background:#fff8e1;padding:14px 24px;border:1px solid #ffe082;border-top:none;font-size:12px;">
    <strong style="color:#b7950b;">Know someone who should receive this?</strong>
    Share the subscription form:
    <a href="https://docs.google.com/forms/d/e/1FAIpQLSdummy/viewform" style="color:#1a5276;">
      Subscribe to ScoutBot &rarr;
    </a>
    &nbsp;|&nbsp;
    <a href="{FUNDRAISING_DOC}" style="color:#1a5276;">Support ScoutBot financially &rarr;</a>
  </div>

  <div style="padding:12px 24px;font-size:11px;color:#aaa;border:1px solid #ddd;border-top:none;">
    ScoutBot &mdash; Open Source &nbsp;|&nbsp;
    <a href="{GITHUB_URL}" style="color:#aaa;">GitHub</a>
    &nbsp;|&nbsp;
    <a href="{SHEET_URL}" style="color:#aaa;">Full Opportunity Sheet</a>
    &nbsp;&mdash;&nbsp; You receive this because you subscribed to ScoutBot alerts.
  </div>

  <div style="padding:10px 24px;font-size:11px;color:#bbb;border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px;background:#fafafa;">
    ⚠️ <em>ScoutBot was vibecoded &mdash; built fast, iterated in public, and prone to the occasional error.
    Always verify opportunities directly at the source before applying.</em>
    &nbsp;&mdash;&nbsp;
    <strong>Better at coding? Hop on the bot and prove it &rarr;</strong>
    <a href="{GITHUB_URL}" style="color:#aaa;">github.com/TechHub-Extensions/ScoutBot</a>
  </div>

</body>
</html>
"""


def _build_personal_email(html_body, subject, recipient_email):
    """Build a personal email message addressed only to the single recipient."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"ScoutBot <{SENDER_EMAIL}>"
    msg["To"]      = recipient_email   # only this person — fully private
    msg.attach(MIMEText(html_body, "html"))
    return msg


def send_email(opps, recipients):
    """
    Send a personal, individually addressed email to every subscriber.
    Recipients are batched into groups of EMAIL_BATCH_SIZE and sent over a
    single SMTP connection per batch to respect Gmail rate limits.
    A pause of EMAIL_BATCH_PAUSE_SEC separates each batch.

    Privacy guarantee: every subscriber receives an email where only their
    own address appears in the To field. No one can see any other subscriber.
    """
    if not SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        logger.error("notify: SENDER_EMAIL or GMAIL_APP_PASSWORD not set.")
        return False
    if not recipients:
        logger.warning("notify: No recipients found.")
        return False

    subject   = (f"ScoutBot \u2014 {len(opps)} Latest Opportunities "
                 f"for Nigerian Students & Founders")
    html_body = build_html(opps)

    batches      = [recipients[i:i + EMAIL_BATCH_SIZE]
                    for i in range(0, len(recipients), EMAIL_BATCH_SIZE)]
    total_batches = len(batches)
    logger.info(
        f"notify: Sending to {len(recipients)} recipients in "
        f"{total_batches} batch(es) of up to {EMAIL_BATCH_SIZE} "
        f"({EMAIL_BATCH_PAUSE_SEC}s pause between batches). "
        f"Each subscriber receives a personal, privately addressed email."
    )

    successes = 0
    for i, batch in enumerate(batches, start=1):
        batch_ok = 0
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
                for email_addr in batch:
                    try:
                        msg = _build_personal_email(html_body, subject, email_addr)
                        server.sendmail(SENDER_EMAIL, [email_addr], msg.as_string())
                        batch_ok += 1
                    except Exception as exc:
                        logger.error(f"notify: Failed to send to {email_addr}: {exc}")
            successes += batch_ok
            logger.info(
                f"notify: Batch {i}/{total_batches} done "
                f"({batch_ok}/{len(batch)} sent)."
            )
        except Exception as exc:
            logger.error(f"notify: Batch {i}/{total_batches} SMTP connection failed: {exc}")

        if i < total_batches:
            logger.info(f"notify: Pausing {EMAIL_BATCH_PAUSE_SEC}s before batch {i + 1}...")
            time.sleep(EMAIL_BATCH_PAUSE_SEC)

    logger.info(f"notify: Complete. {successes}/{len(recipients)} recipients reached.")
    return successes > 0


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("notify: Fetching recent opportunities...")
    opps = fetch_recent_opportunities(limit=30)
    if not opps:
        logger.warning("notify: Sheet empty or unreachable. No email sent.")
        return
    recipients = build_recipient_list()
    send_email(opps, recipients)


if __name__ == "__main__":
    main()
