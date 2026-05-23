"""
ScoutBot — notify.py  (SWE-List Edition)
=========================================

Reads subscriber emails from:
  1. Google Form responses spreadsheet (FORM_SHEET_ID)
  2. "Subscribers" tab in the main opportunities spreadsheet

Sends each subscriber ONE personally addressed email — nobody can
see any other subscriber's address (no BCC, no CC, no group send).

Email design: SWE-List style — clean table, one row per opportunity,
direct apply link, no paragraph blobs, no aggregator summaries.

Staggered delivery: 600 subscribers are sent in configurable batches
with a short sleep between each batch to avoid Gmail SMTP rate limits
and spam triggers. Default: batches of 20, 3-second gap between batches.
"""

import os
import smtplib
import time
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [notify] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scoutbot.notify")

# ── Config ────────────────────────────────────────────────────────────────────

SENDER_EMAIL         = os.getenv("SENDER_EMAIL", "")
GMAIL_APP_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD", "")
SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID", "")
FORM_SHEET_ID        = os.getenv("FORM_SHEET_ID", "")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
FALLBACK_RECIPIENTS  = [
    e.strip()
    for e in os.getenv("RECIPIENT_EMAILS", "").split(",")
    if e.strip()
]

# Stagger settings — tune these to stay within Gmail's limits
# Gmail allows ~500 external recipients / 24 h on a free account.
# With 600 subscribers, a batch size of 20 + 3 s gap finishes in ~90 s.
BATCH_SIZE           = 20    # emails per batch
BATCH_SLEEP_SECONDS  = 3     # seconds to sleep between batches

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Colours — ScoutBot brand palette (professional, dark)
COLOR_BG        = "#0d0d0d"
COLOR_SURFACE   = "#161616"
COLOR_CARD      = "#1e1e1e"
COLOR_BORDER    = "#2a2a2a"
COLOR_ACCENT    = "#f5c518"   # warm gold — like SWE list amber
COLOR_TEXT      = "#e8e8e8"
COLOR_MUTED     = "#888888"
COLOR_LINK      = "#f5c518"
COLOR_BTN_BG    = "#f5c518"
COLOR_BTN_TEXT  = "#0d0d0d"


# ── Google Sheets helpers ─────────────────────────────────────────────────────

def get_gspread_client():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON, scopes=SCOPES)
    return gspread.authorize(creds)


def get_opportunities(client):
    """Read all Open rows from the main spreadsheet. Returns list of dicts."""
    try:
        sh   = client.open_by_key(SPREADSHEET_ID)
        ws   = sh.sheet1
        rows = ws.get_all_records()
        open_rows = [r for r in rows if str(r.get("Status", "")).strip().lower() == "open"]
        log.info(f"Fetched {len(open_rows)} open opportunities from spreadsheet.")
        return open_rows
    except Exception as exc:
        log.error(f"Could not read opportunities: {exc}")
        return []


def get_subscribers(client):
    """
    Collect unique subscriber emails from:
      1. Google Form responses sheet (column 'Email Address')
      2. 'Subscribers' tab in the main sheet (column 'Email')

    Returns a de-duplicated, lowercased list.
    """
    emails = set()

    # Source 1: Form responses
    try:
        form_sh = client.open_by_key(FORM_SHEET_ID)
        form_ws = form_sh.sheet1
        records = form_ws.get_all_records()
        for row in records:
            email = (
                row.get("Email Address")
                or row.get("Email")
                or row.get("email")
                or ""
            )
            email = str(email).strip().lower()
            if "@" in email:
                emails.add(email)
        log.info(f"Form responses: {len(emails)} emails collected.")
    except Exception as exc:
        log.warning(f"Could not read form responses: {exc}")

    # Source 2: Subscribers tab
    try:
        main_sh = client.open_by_key(SPREADSHEET_ID)
        try:
            sub_ws = main_sh.worksheet("Subscribers")
        except gspread.exceptions.WorksheetNotFound:
            sub_ws = None

        if sub_ws:
            sub_records = sub_ws.get_all_records()
            before = len(emails)
            for row in sub_records:
                email = str(row.get("Email", row.get("email", ""))).strip().lower()
                if "@" in email:
                    emails.add(email)
            log.info(f"Subscribers tab added {len(emails) - before} additional emails.")
    except Exception as exc:
        log.warning(f"Could not read Subscribers tab: {exc}")

    # Fallback
    if not emails and FALLBACK_RECIPIENTS:
        log.warning("No subscribers from sheets — using FALLBACK_RECIPIENTS from .env")
        emails = set(e.lower() for e in FALLBACK_RECIPIENTS)

    log.info(f"Total unique subscribers: {len(emails)}")
    return sorted(emails)


# ── Email builder ─────────────────────────────────────────────────────────────

def category_badge(category: str) -> str:
    """Return a styled HTML badge for a category string."""
    colours = {
        "Scholarship":      ("#1a3a5c", "#5ba4e6"),
        "Fellowship":       ("#2a1a5c", "#9b7de8"),
        "Internship":       ("#1a4a2a", "#5be695"),
        "Bootcamp":         ("#4a2a1a", "#e6955b"),
        "Grant":            ("#4a4a1a", "#e6e05b"),
        "Accelerator":      ("#3a1a3a", "#e05be6"),
        "Incubator":        ("#1a3a3a", "#5be6d4"),
        "VC Funding":       ("#3a1a1a", "#e65b5b"),
        "Pitch Competition":("#2a3a1a", "#9be65b"),
        "Award":            ("#3a2a1a", "#e6a95b"),
        "Apprenticeship":   ("#1a2a3a", "#5b9be6"),
        "Conference":       ("#2a2a2a", "#b0b0b0"),
        "Opportunity":      ("#2a2a2a", "#b0b0b0"),
    }
    bg, fg = colours.get(category, ("#2a2a2a", "#b0b0b0"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:4px;font-size:11px;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;">'
        f'{category}</span>'
    )


def range_badge(rng: str) -> str:
    if rng.lower() == "national":
        return (
            '<span style="background:#0f2a0f;color:#4caf50;padding:2px 7px;'
            'border-radius:4px;font-size:10px;font-weight:600;">🇳🇬 Nigeria</span>'
        )
    return (
        '<span style="background:#1a1a2e;color:#5b9be6;padding:2px 7px;'
        'border-radius:4px;font-size:10px;font-weight:600;">🌍 International</span>'
    )


def build_opportunity_row(opp: dict, idx: int) -> str:
    """Render a single opportunity as a clean table row (SWE-List style)."""
    title        = opp.get("Title", "Opportunity")
    org          = opp.get("Organization", "")
    category     = opp.get("Category", "Opportunity")
    rng          = opp.get("Range", "International")
    industry     = opp.get("Industry", "General")
    edu          = opp.get("Education Level", "")
    deadline     = opp.get("Deadline", "")
    summary      = opp.get("Summary", "")
    apply_link   = opp.get("Application Link", "#")

    deadline_html = ""
    if deadline:
        deadline_html = (
            f'<span style="color:{COLOR_MUTED};font-size:11px;">⏳ {deadline}</span>'
        )

    # Alternating row background
    row_bg = COLOR_CARD if idx % 2 == 0 else COLOR_SURFACE

    return f"""
    <tr style="background:{row_bg};">
      <td style="padding:14px 16px;border-bottom:1px solid {COLOR_BORDER};vertical-align:top;">

        <!-- Title + org -->
        <div style="margin-bottom:5px;">
          <a href="{apply_link}"
             style="color:{COLOR_TEXT};font-size:15px;font-weight:600;
                    text-decoration:none;line-height:1.3;">
            {title}
          </a>
          {f'<span style="color:{COLOR_MUTED};font-size:12px;margin-left:6px;">— {org}</span>' if org else ""}
        </div>

        <!-- Badges row -->
        <div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:6px;align-items:center;">
          {category_badge(category)}
          {range_badge(rng)}
          <span style="color:{COLOR_MUTED};font-size:11px;padding:2px 6px;
                        background:#222;border-radius:4px;">{industry}</span>
          {f'<span style="color:{COLOR_MUTED};font-size:11px;padding:2px 6px;background:#222;border-radius:4px;">{edu}</span>' if edu else ""}
          {deadline_html}
        </div>

        <!-- One-line summary -->
        {f'<p style="color:{COLOR_MUTED};font-size:13px;margin:0 0 8px 0;line-height:1.4;">{summary}</p>' if summary else ""}

        <!-- Apply button -->
        <a href="{apply_link}"
           style="display:inline-block;background:{COLOR_BTN_BG};color:{COLOR_BTN_TEXT};
                  padding:6px 14px;border-radius:5px;font-size:12px;font-weight:700;
                  text-decoration:none;letter-spacing:0.3px;">
          Apply →
        </a>

      </td>
    </tr>
    """


def build_email_html(opportunities: list, recipient_email: str) -> str:
    """Build the full HTML email body."""
    today        = datetime.now().strftime("%B %d, %Y")
    total        = len(opportunities)

    # Group by category for section headers
    sections     = {}
    for opp in opportunities:
        cat = opp.get("Category", "Opportunity")
        sections.setdefault(cat, []).append(opp)

    # Build rows grouped by category
    rows_html = ""
    row_idx   = 0
    for cat, opps in sections.items():
        # Section header row
        rows_html += f"""
        <tr>
          <td style="padding:20px 16px 8px 16px;background:{COLOR_BG};
                     border-bottom:2px solid {COLOR_ACCENT};">
            <span style="color:{COLOR_ACCENT};font-size:12px;font-weight:700;
                         text-transform:uppercase;letter-spacing:1px;">
              {cat}s &nbsp;·&nbsp; {len(opps)} listing{'s' if len(opps) != 1 else ''}
            </span>
          </td>
        </tr>
        """
        for opp in opps:
            rows_html += build_opportunity_row(opp, row_idx)
            row_idx += 1

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>ScoutBot Digest — {today}</title>
</head>
<body style="margin:0;padding:0;background:{COLOR_BG};font-family:'Helvetica Neue',Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:{COLOR_BG};padding:24px 0;">
  <tr><td align="center">
  <table width="640" cellpadding="0" cellspacing="0"
         style="max-width:640px;width:100%;">

    <!-- ── Header ── -->
    <tr>
      <td style="background:{COLOR_SURFACE};padding:28px 24px;
                 border-bottom:3px solid {COLOR_ACCENT};border-radius:8px 8px 0 0;">
        <table width="100%"><tr>
          <td>
            <span style="color:{COLOR_ACCENT};font-size:22px;font-weight:800;
                         letter-spacing:-0.5px;">ScoutBot</span>
            <span style="color:{COLOR_MUTED};font-size:13px;margin-left:10px;">
              Daily Opportunities Digest
            </span>
          </td>
          <td align="right">
            <span style="color:{COLOR_MUTED};font-size:12px;">{today}</span>
          </td>
        </tr></table>
        <p style="color:{COLOR_MUTED};font-size:13px;margin:10px 0 0 0;">
          {total} curated opportunit{'ies' if total != 1 else 'y'} across scholarships,
          fellowships, internships, grants, and startup funding —
          Nigeria · Africa · Global.
        </p>
      </td>
    </tr>

    <!-- ── Opportunities table ── -->
    <tr>
      <td style="background:{COLOR_BG};padding:0;">
        <table width="100%" cellpadding="0" cellspacing="0">
          {rows_html}
        </table>
      </td>
    </tr>

    <!-- ── Footer ── -->
    <tr>
      <td style="background:{COLOR_SURFACE};padding:24px;
                 border-top:1px solid {COLOR_BORDER};
                 border-radius:0 0 8px 8px;text-align:center;">
        <p style="color:{COLOR_MUTED};font-size:12px;margin:0 0 8px 0;">
          You are receiving this because you subscribed to ScoutBot.<br/>
          Always verify deadlines directly on the official opportunity page before applying.
        </p>
        <p style="color:{COLOR_MUTED};font-size:11px;margin:0;">
          ScoutBot is open-source and free. Built by Nigerian students for Nigerian students.<br/>
          This email was sent only to you — your address is not shared with any other subscriber.
        </p>
        <p style="margin:12px 0 0 0;">
          <a href="https://github.com/TechHub-Extensions/ScoutBot"
             style="color:{COLOR_ACCENT};font-size:11px;text-decoration:none;">
            GitHub ↗
          </a>
        </p>
      </td>
    </tr>

  </table>
  </td></tr>
  </table>

</body>
</html>
    """.strip()


# ── SMTP sender ───────────────────────────────────────────────────────────────

def send_email_to(recipient: str, subject: str, html_body: str) -> bool:
    """Send a single personally-addressed email. Returns True on success."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"ScoutBot <{SENDER_EMAIL}>"
    msg["To"]      = recipient          # only THIS recipient's address appears here
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, [recipient], msg.as_string())
        return True
    except Exception as exc:
        log.error(f"Failed to send to {recipient}: {exc}")
        return False


def send_digest(opportunities: list, subscribers: list):
    """
    Send the daily digest to every subscriber.

    Delivery model:
      • Each email is individually addressed — To: contains only that
        subscriber's own address. No CC, no BCC, no group header.
      • Sends are staggered: BATCH_SIZE emails per batch, then
        BATCH_SLEEP_SECONDS pause before the next batch.
      • This keeps Gmail from triggering spam / bulk-mail filters
        while handling ~600 recipients within a few minutes.
    """
    if not opportunities:
        log.warning("No open opportunities to send. Aborting digest.")
        return

    if not subscribers:
        log.warning("No subscribers found. Aborting digest.")
        return

    today   = datetime.now().strftime("%B %d, %Y")
    subject = f"ScoutBot — {len(opportunities)} Opportunities | {today}"
    total   = len(subscribers)
    sent    = 0
    failed  = 0

    log.info(
        f"Starting digest: {len(opportunities)} opps → {total} subscribers "
        f"(batches of {BATCH_SIZE}, {BATCH_SLEEP_SECONDS}s gap)"
    )

    for batch_start in range(0, total, BATCH_SIZE):
        batch = subscribers[batch_start : batch_start + BATCH_SIZE]

        for recipient in batch:
            # Build a fresh HTML body per recipient (personalisation-ready)
            html_body = build_email_html(opportunities, recipient)
            ok = send_email_to(recipient, subject, html_body)
            if ok:
                sent += 1
            else:
                failed += 1

        batch_end = min(batch_start + BATCH_SIZE, total)
        log.info(
            f"Batch {batch_start + 1}–{batch_end} / {total} sent. "
            f"(ok={sent}, fail={failed})"
        )

        # Sleep between batches — skip after the last one
        if batch_end < total:
            time.sleep(BATCH_SLEEP_SECONDS)

    log.info(f"Digest complete. Sent: {sent} | Failed: {failed} | Total: {total}")


# ── Entry point ───────────────────────────────────────────────────────────────

def run_notify():
    log.info("ScoutBot notify — starting.")
    client        = get_gspread_client()
    opportunities = get_opportunities(client)
    subscribers   = get_subscribers(client)
    send_digest(opportunities, subscribers)
    log.info("ScoutBot notify — done.")


if __name__ == "__main__":
    run_notify()
