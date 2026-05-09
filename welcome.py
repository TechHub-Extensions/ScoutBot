"""
welcome.py — Send the ScoutBot welcome/intro email to all unique subscribers.

Reads from:
  - Main spreadsheet Subscribers tab
  - Google Form responses sheet
Deduplicates, then sends a private individual email to every address.
Batches of 30 with 6-minute pauses to stay within Gmail limits.

Usage:
  python welcome.py
"""

import smtplib, time, os, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
import gspread

load_dotenv()

SENDER_EMAIL   = os.getenv("SENDER_EMAIL", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASSWORD", "")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
FORM_SHEET_ID  = os.getenv("FORM_SHEET_ID", "1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s")
SA_FILE        = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

SUBJECT = "Welcome to ScoutBot — your daily opportunity digest"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body{{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0}}
    .wrapper{{max-width:600px;margin:30px auto;background:#fff;border-radius:10px;
              overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
    .header{{background:#1a1a2e;color:#fff;padding:32px 36px 24px}}
    .header h1{{margin:0 0 6px;font-size:24px}}
    .header p{{margin:0;font-size:14px;color:#aab2c8}}
    .body{{padding:32px 36px;color:#333;line-height:1.7;font-size:15px}}
    .body p{{margin:0 0 16px}}
    .card{{background:#f8f9ff;border-left:4px solid #4a6cf7;border-radius:6px;
           padding:16px 20px;margin:20px 0}}
    .card a{{color:#4a6cf7;text-decoration:none;font-weight:bold}}
    .card a:hover{{text-decoration:underline}}
    .card .label{{font-size:12px;text-transform:uppercase;letter-spacing:.5px;
                  color:#888;margin-bottom:4px}}
    .footer{{background:#f0f0f0;text-align:center;padding:20px 36px;
             font-size:12px;color:#888}}
    .footer a{{color:#4a6cf7;text-decoration:none}}
    .badge{{display:inline-block;background:#e8edff;color:#4a6cf7;border-radius:20px;
            padding:2px 12px;font-size:13px;font-weight:bold}}
  </style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>Welcome to ScoutBot</h1>
    <p>Your daily student opportunity digest</p>
  </div>
  <div class="body">
    <p>Hi there!</p>
    <p>
      I'm <strong>Kamsi</strong> — co-lead of the
      <span class="badge">Cowrywise Ambassador Community, Lead City University</span>
      and the person behind ScoutBot.
      You're receiving this because you're subscribed to or have access to our
      opportunities spreadsheet.
    </p>
    <p>
      <strong>Here's what ScoutBot does:</strong><br>
      We automatically scrape 15+ sources every day and send you a digest of the
      freshest scholarships, fellowships, internships, bootcamps, grants, and startup
      funding opportunities — organised neatly, delivered privately to your inbox
      <em>approximately twice a day</em> (7 AM &amp; 7 PM Lagos time).
      We also delist expired opportunities so the list stays clean.
    </p>

    <div class="card">
      <div class="label">Share the bot</div>
      Help other students subscribe — send them this form:<br>
      <a href="https://docs.google.com/forms/d/e/1FAIpQLSdCxs6tRDwFw1W9L-U1BgWU1MnogT0eHTEZ1-kWSvmzotRGiw/viewform?usp=header">
        &#8594; Subscribe to ScoutBot
      </a>
    </div>

    <div class="card">
      <div class="label">Our goals &amp; fundraising</div>
      We're raising &#x20A6;2M to run Twitter/X ads and reach 4,000 students
      in 6 months. Read about our plan and how to contribute:<br>
      <a href="https://docs.google.com/document/d/1SqxaAg4tvuWp3LgGzqSSSw4_bxBWHmgmrQ9IyyKHtE8/edit">
        &#8594; Read the fundraising document
      </a>
    </div>

    <div class="card">
      <div class="label">Contribute technically</div>
      ScoutBot is open-source. If you'd like to help build or improve it:<br>
      <a href="https://github.com/TechHub-Extensions/ScoutBot">
        &#8594; View on GitHub
      </a>
    </div>

    <p style="margin-top:28px;">
      Questions or want to get in touch? Reach me directly:<br>
      <a href="mailto:kamsirichard1960@gmail.com" style="color:#4a6cf7;">
        kamsirichard1960@gmail.com
      </a>
    </p>
    <p>Glad to have you here.<br><strong>&#8212; Kamsi</strong></p>
  </div>
  <div class="footer">
    You're receiving this because you're subscribed to ScoutBot.<br>
    To unsubscribe, email
    <a href="mailto:kamsirichard1960@gmail.com">kamsirichard1960@gmail.com</a>.
  </div>
  <div style="background:#f7f7f7;text-align:center;padding:12px 36px;font-size:11px;color:#bbb;border-top:1px solid #e8e8e8;">
    &#9888;&#65039; <em>ScoutBot was vibecoded &mdash; built fast, iterated in public, and prone to the occasional error.
    Always verify opportunities at the source before applying.</em><br>
    <strong style="color:#aaa;">Better at coding? Hop on the bot and prove it &rarr;</strong>
    <a href="https://github.com/TechHub-Extensions/ScoutBot" style="color:#aaa;">
      github.com/TechHub-Extensions/ScoutBot
    </a>
  </div>
</div>
</body>
</html>"""


def load_all_subscribers():
    creds = Credentials.from_service_account_file(
        SA_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)

    sub_ws = gc.open_by_key(SPREADSHEET_ID).worksheet("Subscribers")
    sub_emails = [
        r[1].strip() for r in sub_ws.get_all_values()[2:]
        if len(r) > 1 and r[1].strip()
    ]

    form_emails = []
    if FORM_SHEET_ID:
        form_ws = gc.open_by_key(FORM_SHEET_ID).sheet1
        form_emails = [
            r[3].strip() for r in form_ws.get_all_values()[1:]
            if len(r) > 3 and r[3].strip()
        ]

    seen, unique = set(), []
    for e in sub_emails + form_emails:
        if e.lower() not in seen:
            seen.add(e.lower())
            unique.append(e)
    return unique


def send_welcome(recipients=None):
    if recipients is None:
        recipients = load_all_subscribers()

    print(f"Sending welcome email to {len(recipients)} subscribers...")

    BATCH_SIZE = 30
    PAUSE_SECS = 360   # 6 minutes between batches

    sent, failed = 0, []

    for i, recipient in enumerate(recipients):
        if i > 0 and i % BATCH_SIZE == 0:
            print(f"  Batch {i // BATCH_SIZE} done ({i}/{len(recipients)}). "
                  f"Pausing {PAUSE_SECS // 60} min...")
            time.sleep(PAUSE_SECS)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = SUBJECT
            msg["From"]    = f"ScoutBot <{SENDER_EMAIL}>"
            msg["To"]      = recipient
            msg.attach(MIMEText(HTML_TEMPLATE, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(SENDER_EMAIL, GMAIL_APP_PASS)
                smtp.sendmail(SENDER_EMAIL, recipient, msg.as_string())

            sent += 1
            print(f"  ✅ [{sent}/{len(recipients)}] {recipient}")

        except Exception as e:
            failed.append(recipient)
            print(f"  ❌ {recipient}: {e}")

    print(f"\nWelcome send complete — sent: {sent}, failed: {len(failed)}")
    return sent, failed


if __name__ == "__main__":
    send_welcome()
