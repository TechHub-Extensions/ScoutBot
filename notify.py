"""
ScoutBot — Weekly Email Digest

Sends a SWElist-style clean weekly digest to all verified subscribers.
Bounce tracking: permanently rejected addresses are stored in a "Bounced"
tab and excluded from all future sends.

Email contains two sections:
  🇳🇬 Nigeria    — entries from the Nigeria tab added in the last 7 days
  🌍 International — entries from the International tab added in the last 7 days
"""

import os
import re
import imaplib
import smtplib
import argparse
import logging
import time
from datetime import date, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SENDER_EMAIL         = os.getenv("SENDER_EMAIL", "")
GMAIL_APP_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
FORM_SHEET_ID        = os.getenv("FORM_SHEET_ID", "1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s")
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
EMAIL_BATCH_PAUSE_SEC = int(os.getenv("EMAIL_BATCH_PAUSE_SEC", "360"))

RECENT_DAYS = 7   # Only include opportunities added within this many days
EMAIL_PREVIEW_PATH = Path(__file__).resolve().parent / "email_preview.html"

SHEET_URL       = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
FUNDRAISING_DOC = "https://docs.google.com/document/d/1SqxaAg4tvuWp3LgGzqSSSw4_bxBWHmgmrQ9IyyKHtE8/edit"
GITHUB_URL      = "https://github.com/TechHub-Extensions/ScoutBot"

_GMAIL_SEARCH = (
    "https://mail.google.com/mail/u/0/#search/"
    "from%3Akamsirichard1960%40gmail.com+subject%3AScoutBot"
)
_UNSUB_MAILTO = (
    f"mailto:{SENDER_EMAIL}"
    "?subject=Unsubscribe%20from%20ScoutBot"
    "&body=Please%20remove%20me%20from%20the%20ScoutBot%20mailing%20list."
)

# Basic format validation — rejects obviously malformed addresses
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

# Domains that never deliver (disposable, test, placeholder)
_INVALID_DOMAINS = {
    "example.com", "test.com", "mailinator.com", "guerrillamail.com",
    "sharklasers.com", "guerrillamailblock.com", "grr.la", "yopmail.com",
    "trashmail.com", "dispostable.com", "tempmail.com", "throwam.com",
}


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


def is_valid_email(addr):
    if not addr or not _EMAIL_RE.match(addr):
        return False
    domain = addr.split("@", 1)[1].lower()
    if domain in _INVALID_DOMAINS:
        return False
    return True


# ── Bounce tracking ─────────────────────────────────────────────────────────

def fetch_bounced_emails():
    """Load addresses from the Bounced tab (column A). Returns a set."""
    try:
        client = _get_sheet_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        try:
            ws = ss.worksheet("Bounced")
        except Exception:
            return set()
        values = ws.col_values(1)
        bounced = {v.strip().lower() for v in values[1:] if v.strip() and "@" in v}
        logger.info(f"notify: {len(bounced)} bounced addresses loaded.")
        return bounced
    except Exception as exc:
        logger.error(f"notify: Could not load Bounced tab — {exc}")
        return set()


def record_bounces(bad_addresses):
    """Append newly-bounced addresses to the Bounced tab (creates tab if needed)."""
    if not bad_addresses:
        return
    try:
        client = _get_sheet_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        try:
            ws = ss.worksheet("Bounced")
        except Exception:
            ws = ss.add_worksheet(title="Bounced", rows=500, cols=3)
            ws.append_row(["Email", "Date", "Reason"])
            logger.info("notify: Created Bounced tab.")

        today = date.today().isoformat()
        rows = [[addr, today, "SMTP rejected"] for addr in bad_addresses]
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info(f"notify: Recorded {len(bad_addresses)} new bounced address(es).")
    except Exception as exc:
        logger.error(f"notify: Could not record bounces — {exc}")


# ── Subscriber list ──────────────────────────────────────────────────────────

def fetch_form_subscribers():
    try:
        client = _get_sheet_client()
        ws = client.open_by_key(FORM_SHEET_ID).worksheets()[0]
        emails = [v.strip().lower() for v in ws.col_values(4)[1:] if v.strip() and "@" in v]
        logger.info(f"notify: {len(emails)} emails from Form responses.")
        return emails
    except Exception as exc:
        logger.error(f"notify: Form sheet error — {exc}")
        return []


def fetch_subscribers_tab():
    try:
        client = _get_sheet_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        try:
            ws = ss.worksheet("Subscribers")
        except Exception:
            return []
        emails = [v.strip().lower() for v in ws.col_values(2)[2:] if v.strip() and "@" in v]
        logger.info(f"notify: {len(emails)} emails from Subscribers tab.")
        return emails
    except Exception as exc:
        logger.error(f"notify: Subscribers tab error — {exc}")
        return []


def build_recipient_list():
    """
    Merge all sources, deduplicate, validate format, and exclude bounced addresses.
    """
    bounced = fetch_bounced_emails()
    combined = fetch_form_subscribers() + fetch_subscribers_tab() + _ENV_EMAILS
    seen, result = set(), []
    invalid_count = 0
    for e in combined:
        if not e or e in seen:
            continue
        seen.add(e)
        if e in bounced:
            continue
        if not is_valid_email(e):
            invalid_count += 1
            continue
        result.append(e)

    logger.info(
        f"notify: {len(result)} valid recipients "
        f"(skipped {len(bounced)} bounced, {invalid_count} invalid format)."
    )
    return result


# ── Opportunity data ─────────────────────────────────────────────────────────

def fetch_recent_from_tab(tab_name, limit=25):
    """Fetch up to `limit` entries added in the last RECENT_DAYS days."""
    try:
        client = _get_sheet_client()
        ss = client.open_by_key(SPREADSHEET_ID)
        try:
            ws = ss.worksheet(tab_name)
        except Exception:
            logger.warning(f"notify: Tab '{tab_name}' not found.")
            return []

        rows = ws.get_all_records()
        cutoff = date.today() - timedelta(days=RECENT_DAYS)
        recent = []

        for row in rows:
            date_added_str = str(row.get("Date Added", "")).strip()
            if date_added_str:
                try:
                    from dateutil.parser import parse as dp
                    if dp(date_added_str, fuzzy=True).date() >= cutoff:
                        recent.append(row)
                except Exception:
                    recent.append(row)
            else:
                recent.append(row)   # legacy rows without Date Added

        result = recent[-limit:] if len(recent) > limit else recent
        logger.info(f"notify: {len(result)} recent entries from '{tab_name}'.")
        return result
    except Exception as exc:
        logger.error(f"notify: Could not fetch '{tab_name}' — {exc}")
        return []


# ── Email HTML (SWElist-inspired clean format) ───────────────────────────────

def _opp_list_items(opps):
    """Build clean list items — one opportunity per line, link + deadline."""
    CATEGORY_COLORS = {
        "Scholarship":    "#1a5276",
        "Fellowship":     "#6c3483",
        "Internship":     "#117a65",
        "Bootcamp":       "#b7950b",
        "Apprenticeship": "#784212",
        "Conference":     "#1f618d",
        "Competition":    "#922b21",
        "Award":          "#7d6608",
        "Opportunity":    "#555",
    }
    html = ""
    for opp in reversed(opps):
        link     = opp.get("Application Link", "#")
        title    = opp.get("Title", "Untitled")
        cat      = opp.get("Category", "Opportunity")
        industry = opp.get("Industry", "")
        deadline = opp.get("Deadline", "")
        color    = CATEGORY_COLORS.get(cat, "#555")
        badge    = (
            f'<span style="display:inline-block;background:{color};color:#fff;'
            f'padding:2px 8px;border-radius:3px;font-size:12px;'
            f'font-weight:600;margin-right:4px;">{cat}</span>'
        )
        dl_html  = (
            f'&nbsp;·&nbsp;<span style="color:#e74c3c;font-weight:600;">Due: {deadline}</span>'
            if deadline else ""
        )
        ind_html = f'&nbsp;·&nbsp;{industry}' if industry and industry != "General" else ""
        html += f"""
        <li class="opportunity-item"
            style="padding:12px 0;border-bottom:1px solid #f0f0f0;list-style:none;">
          <a class="opportunity-title" href="{link}" target="_blank"
             style="color:#1a1a2e;font-weight:600;font-size:15px;line-height:1.45;text-decoration:none;">
            {title}</a>
          <a class="apply-link" href="{link}" target="_blank"
             style="color:#27ae60;font-size:14px;line-height:44px;text-decoration:none;font-weight:700;margin-left:6px;white-space:nowrap;">
            Apply&nbsp;→</a><br>
          <span style="font-size:13px;line-height:1.5;color:#777;">{badge}{ind_html}{dl_html}</span>
        </li>"""
    return html


def _section_block(emoji, label, count, opps, accent):
    if not opps:
        return f"""
        <p style="color:#aaa;font-size:13px;margin:16px 0 0;">
          {emoji} <strong>{label}</strong> — No new opportunities this week.
        </p>"""
    return f"""
    <h3 style="color:{accent};border-left:4px solid {accent};padding-left:10px;
               margin:24px 0 8px;font-size:16px;">
      {emoji} {label}
      <span style="font-size:12px;font-weight:normal;color:#888;"> — {count} this week</span>
    </h3>
    <ul style="padding:0;margin:0;">{_opp_list_items(opps)}</ul>"""


def build_html(nigeria_opps, intl_opps):
    total    = len(nigeria_opps) + len(intl_opps)
    week_end = date.today()
    week_start = week_end - timedelta(days=6)
    span_str = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"

    nigeria_block = _section_block("🇳🇬", "Nigeria", len(nigeria_opps), nigeria_opps, "#1a5276")
    intl_block    = _section_block("🌍", "International", len(intl_opps), intl_opps, "#1d6348")

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    @media only screen and (max-width: 480px) {{
      body {{ padding: 18px 12px !important; }}
      .email-shell {{ width: 100% !important; }}
      .digest-title {{ font-size: 22px !important; line-height: 1.25 !important; }}
      .intro-copy, .opportunity-title {{ font-size: 15px !important; }}
      .apply-link {{
        display: inline-block !important;
        min-height: 44px !important;
        line-height: 44px !important;
        padding: 0 2px !important;
      }}
      .footer-links a {{
        display: inline-block !important;
        min-height: 44px !important;
        line-height: 44px !important;
        margin-right: 12px !important;
      }}
    }}
  </style>
</head>
<body style="font-family:'Segoe UI',Arial,sans-serif;color:#1a1a1a;max-width:620px;
             margin:auto;padding:24px 16px;background:#fff;">

  <div class="email-shell" style="width:100%;max-width:620px;margin:0 auto;">
  <div style="border-bottom:3px solid #1a1a2e;padding-bottom:12px;margin-bottom:18px;">
    <h2 class="digest-title" style="margin:0;color:#1a1a2e;font-size:20px;line-height:1.3;">ScoutBot — Weekly Digest</h2>
    <p style="margin:4px 0 0;color:#777;font-size:13px;">{span_str} &nbsp;·&nbsp; {total} fresh opportunities</p>
  </div>

  <p style="font-size:15px;line-height:1.6;">
    Hey! Here are this week's student opportunities — <strong>only listings added in the last 7 days</strong>.
    Click <strong>Apply →</strong> to go straight to the application page.
  </p>

  {nigeria_block}
  {intl_block}

  <div style="margin-top:28px;padding-top:12px;border-top:1px solid #eee;font-size:13px;">
    <a href="{SHEET_URL}" style="color:#1a5276;">📋 Full spreadsheet &rarr;</a>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="{FUNDRAISING_DOC}" style="color:#888;">Support ScoutBot</a>
  </div>

  <!-- ── inbox cleanup ─────────────────────────────────────────────────── -->
  <div style="margin:18px 0 0;background:#fafafa;border:1px solid #e0e0e0;border-radius:7px;padding:14px 16px;">
    <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#555;">🗑 Too many old ScoutBot emails?</p>
    <p style="margin:0 0 10px;font-size:12px;color:#888;line-height:1.6;">
      Click below → Gmail opens showing all ScoutBot emails →
      tick the top checkbox → <em>"Select all conversations"</em> → 🗑 Delete.
    </p>
    <a href="{_GMAIL_SEARCH}"
       style="display:inline-block;background:#e74c3c;color:#fff;font-weight:600;
              padding:8px 18px;border-radius:5px;text-decoration:none;font-size:12px;">
      Open Gmail &amp; delete all ScoutBot emails →
    </a>
    <span style="font-size:11px;color:#bbb;margin-left:10px;">
      Or search: <code>from:kamsirichard1960@gmail.com</code>
    </span>
  </div>
  <!-- ────────────────────────────────────────────────────────────────────── -->

  <div style="margin-top:12px;padding:8px 0;font-size:12px;color:#bbb;">
    <a href="{_UNSUB_MAILTO}" style="color:#c0392b;">Unsubscribe</a>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    <a href="{GITHUB_URL}" style="color:#aaa;">GitHub</a>
    <br><span style="font-size:11px;">ScoutBot is open source &amp; student-built. Always verify opportunities at source.</span>
  </div>

</body>
</html>"""


# ── Send ─────────────────────────────────────────────────────────────────────

def build_subject(nigeria_opps, intl_opps):
    total = len(nigeria_opps) + len(intl_opps)
    return f"ScoutBot Weekly — {total} Fresh Opportunities ({date.today().strftime('%b %d')})"


def write_email_preview(html, subject, recipients, preview_path=EMAIL_PREVIEW_PATH):
    preview_path.write_text(html, encoding="utf-8")
    print(f"Subject: {subject}")
    print(f"Recipients: {len(recipients)}")
    print(f"HTML preview written to: {preview_path.name}")
    logger.info(f"notify: Dry run — preview written to {preview_path}.")
    return preview_path


def _build_personal_email(html_body, subject, recipient_email):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"ScoutBot <{SENDER_EMAIL}>"
    msg["To"]      = recipient_email
    msg.attach(MIMEText(html_body, "html"))
    return msg


def send_email(nigeria_opps, intl_opps, recipients):
    if not SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        logger.error("notify: SENDER_EMAIL or GMAIL_APP_PASSWORD not set.")
        return False
    if not recipients:
        logger.warning("notify: No recipients.")
        return False

    subject = build_subject(nigeria_opps, intl_opps)
    html    = build_html(nigeria_opps, intl_opps)

    batches       = [recipients[i:i + EMAIL_BATCH_SIZE]
                     for i in range(0, len(recipients), EMAIL_BATCH_SIZE)]
    total_batches = len(batches)
    logger.info(f"notify: Sending to {len(recipients)} recipients in {total_batches} batch(es).")

    successes  = 0
    all_bounced = []

    for i, batch in enumerate(batches, start=1):
        batch_ok = 0
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
                for addr in batch:
                    try:
                        msg = _build_personal_email(html, subject, addr)
                        server.sendmail(SENDER_EMAIL, [addr], msg.as_string())
                        batch_ok += 1
                    except smtplib.SMTPRecipientsRefused:
                        # Hard bounce — recipient permanently rejected by their server
                        logger.warning(f"notify: Hard bounce for {addr} — adding to Bounced list.")
                        all_bounced.append(addr)
                    except Exception as exc:
                        logger.error(f"notify: Failed to send to {addr}: {exc}")
            successes += batch_ok
            logger.info(f"notify: Batch {i}/{total_batches} — {batch_ok}/{len(batch)} sent.")
        except Exception as exc:
            logger.error(f"notify: Batch {i}/{total_batches} SMTP error — {exc}")

        if i < total_batches:
            logger.info(f"notify: Pausing {EMAIL_BATCH_PAUSE_SEC}s...")
            time.sleep(EMAIL_BATCH_PAUSE_SEC)

    # Persist any hard bounces so future runs skip them
    if all_bounced:
        record_bounces(all_bounced)

    logger.info(f"notify: Done. {successes}/{len(recipients)} delivered, {len(all_bounced)} bounced.")
    return successes > 0


def purge_sent_scoutbot_emails():
    """
    Connect to Gmail via IMAP and permanently delete every ScoutBot digest
    email from the Sent folder.  Silently skips if credentials are missing.
    """
    if not SENDER_EMAIL or not GMAIL_APP_PASSWORD:
        return
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)

        # Gmail stores sent mail in "[Gmail]/Sent Mail"
        status, _ = mail.select('"[Gmail]/Sent Mail"')
        if status != "OK":
            mail.logout()
            return

        # Find all ScoutBot digest emails by subject prefix
        _, data = mail.search(None, 'SUBJECT "ScoutBot"')
        msg_ids = data[0].split() if data[0] else []

        if msg_ids:
            # Mark all matches as deleted
            mail.store(b",".join(msg_ids), "+FLAGS", "\\Deleted")
            mail.expunge()
            logger.info(f"notify: Purged {len(msg_ids)} ScoutBot email(s) from Sent folder.")
        else:
            logger.info("notify: No ScoutBot emails found in Sent folder.")

        mail.close()
        mail.logout()
    except Exception as exc:
        logger.warning(f"notify: Could not purge Sent folder — {exc}")


def run_notify(dry_run=False):
    nigeria_opps = fetch_recent_from_tab("Nigeria",       limit=25)
    intl_opps    = fetch_recent_from_tab("International", limit=25)

    if not nigeria_opps and not intl_opps and not dry_run:
        logger.warning("notify: No recent opportunities. No email sent.")
        return False
    if not nigeria_opps and not intl_opps:
        logger.warning("notify: No recent opportunities; writing empty dry-run preview.")

    recipients = build_recipient_list()

    if dry_run:
        subject = build_subject(nigeria_opps, intl_opps)
        html    = build_html(nigeria_opps, intl_opps)
        write_email_preview(html, subject, recipients)
        return True

    result = send_email(nigeria_opps, intl_opps, recipients)
    purge_sent_scoutbot_emails()
    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="ScoutBot weekly email digest")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Build email_preview.html without sending any email"
    )
    args = parser.parse_args()
    run_notify(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
