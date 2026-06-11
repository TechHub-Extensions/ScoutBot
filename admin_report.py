"""
ScoutBot — Monthly Admin Report

Sends a concise summary email to the project lead at the start of each month.
Covers the previous calendar month's activity across both tabs.

Run via GitHub Actions on the 1st of each month (see admin-report.yml).
Can also be triggered manually:

    python admin_report.py

Contents:
  - New opportunities added last 30 days (Nigeria + International)
  - Category breakdown of new entries
  - Total entries currently live in sheet
  - Total active subscribers
  - New bounces this month
  - Top 5 categories by volume (all-time)
"""

import os
import smtplib
import logging
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SENDER_EMAIL       = os.getenv("SENDER_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
ADMIN_EMAIL        = os.getenv("ADMIN_EMAIL", "kamsirichard1960@gmail.com")
SPREADSHEET_ID     = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
FORM_SHEET_ID      = os.getenv("FORM_SHEET_ID", "1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")


# ── Sheet helpers ────────────────────────────────────────────────────────────

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


def _parse_date(raw: str) -> date | None:
    """Parse a Date Added cell into a date object. Returns None on failure."""
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ── Data collection ──────────────────────────────────────────────────────────

def collect_stats(window_days: int = 30) -> dict:
    """
    Pull stats from the Google Sheet.

    Returns a dict with:
      nigeria_total, nigeria_new, intl_total, intl_new,
      categories_new (Counter), subscribers, bounced_new, bounced_total
    """
    client = _get_sheet_client()
    ss = client.open_by_key(SPREADSHEET_ID)

    cutoff = date.today() - timedelta(days=window_days)

    def tab_stats(ws_name: str) -> tuple[int, int, dict]:
        """Returns (total_rows, new_in_window, category_counts_new)."""
        try:
            ws = ss.worksheet(ws_name)
        except Exception:
            logger.warning(f"admin_report: worksheet '{ws_name}' not found.")
            return 0, 0, {}

        records = ws.get_all_records()
        total = len(records)
        new_count = 0
        cats: dict[str, int] = {}

        for row in records:
            raw_date = str(row.get("Date Added", "") or "")
            d = _parse_date(raw_date)
            if d and d >= cutoff:
                new_count += 1
                cat = str(row.get("Category", "Unknown") or "Unknown").strip()
                cats[cat] = cats.get(cat, 0) + 1

        return total, new_count, cats

    # Opportunity tabs
    nigeria_total, nigeria_new, nigeria_cats = tab_stats("Nigeria")
    intl_total, intl_new, intl_cats = tab_stats("International")

    # Merge category counters
    all_cats_new: dict[str, int] = {}
    for k, v in {**nigeria_cats, **intl_cats}.items():
        all_cats_new[k] = all_cats_new.get(k, 0) + v

    # Subscriber count (from the form responses sheet)
    subscribers = 0
    try:
        form_ss = client.open_by_key(FORM_SHEET_ID)
        # Try common worksheet names
        for ws_name in ("Form Responses 1", "Subscribers", "Sheet1"):
            try:
                ws = form_ss.worksheet(ws_name)
                rows = ws.get_all_values()
                subscribers = max(0, len(rows) - 1)  # subtract header
                break
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"admin_report: could not read subscriber count — {e}")

    # Bounced addresses
    bounced_total = 0
    bounced_new = 0
    try:
        ws_b = ss.worksheet("Bounced")
        bounce_rows = ws_b.get_all_records()
        bounced_total = len(bounce_rows)
        for row in bounce_rows:
            raw_date = str(row.get("Date", "") or row.get("Date Added", "") or "")
            d = _parse_date(raw_date)
            if d and d >= cutoff:
                bounced_new += 1
    except Exception:
        pass  # No Bounced tab — not an error

    return {
        "nigeria_total":   nigeria_total,
        "nigeria_new":     nigeria_new,
        "intl_total":      intl_total,
        "intl_new":        intl_new,
        "total_live":      nigeria_total + intl_total,
        "total_new":       nigeria_new + intl_new,
        "categories_new":  all_cats_new,
        "subscribers":     subscribers,
        "bounced_new":     bounced_new,
        "bounced_total":   bounced_total,
        "window_days":     window_days,
        "report_date":     date.today().strftime("%B %Y"),
        "cutoff":          cutoff.strftime("%d %b %Y"),
    }


# ── Email composition ────────────────────────────────────────────────────────

def _category_rows(cats: dict) -> str:
    if not cats:
        return "<tr><td colspan='2' style='color:#9ca3af;padding:4px 0;'>No new entries</td></tr>"
    rows = ""
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        rows += (
            f"<tr>"
            f"<td style='padding:4px 8px 4px 0;color:#374151;'>{cat}</td>"
            f"<td style='padding:4px 0;font-weight:600;color:#1d4ed8;'>{count}</td>"
            f"</tr>"
        )
    return rows


def build_email_html(stats: dict) -> str:
    sheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"
    actions_url = "https://github.com/TechHub-Extensions/ScoutBot/actions"

    bounce_row = ""
    if stats["bounced_new"] > 0:
        bounce_row = (
            f"<tr style='background:#fef2f2;'>"
            f"<td style='padding:10px 16px;border-bottom:1px solid #fecaca;font-weight:600;color:#dc2626;'>⚠️ New bounces this month</td>"
            f"<td style='padding:10px 16px;border-bottom:1px solid #fecaca;font-weight:700;color:#dc2626;'>{stats['bounced_new']}</td>"
            f"</tr>"
        )

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;max-width:600px;">

  <!-- Header -->
  <tr style="background:#1e3a5f;">
    <td style="padding:28px 32px;">
      <p style="margin:0;color:#93c5fd;font-size:0.85em;letter-spacing:1px;text-transform:uppercase;">ScoutBot Admin Report</p>
      <h1 style="margin:6px 0 0;color:#ffffff;font-size:1.5em;font-weight:700;">{stats["report_date"]}</h1>
      <p style="margin:6px 0 0;color:#bfdbfe;font-size:0.9em;">Covering the last {stats["window_days"]} days (since {stats["cutoff"]})</p>
    </td>
  </tr>

  <!-- Headline stats -->
  <tr>
    <td style="padding:28px 32px 0;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="background:#eff6ff;border-radius:10px;padding:18px;width:48%;">
            <p style="margin:0;font-size:2em;font-weight:800;color:#1d4ed8;">{stats["total_new"]}</p>
            <p style="margin:4px 0 0;font-size:0.82em;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">New this month</p>
          </td>
          <td width="4%"></td>
          <td align="center" style="background:#f0fdf4;border-radius:10px;padding:18px;width:48%;">
            <p style="margin:0;font-size:2em;font-weight:800;color:#15803d;">{stats["total_live"]}</p>
            <p style="margin:4px 0 0;font-size:0.82em;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Live in sheet</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Tab breakdown -->
  <tr>
    <td style="padding:24px 32px 0;">
      <h2 style="margin:0 0 12px;font-size:1em;color:#374151;font-weight:700;">Tab breakdown — new entries this month</h2>
      <table width="100%" style="border-collapse:collapse;">
        <tr style="background:#f9fafb;">
          <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;color:#374151;">🇳🇬 Nigeria tab</td>
          <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;font-weight:700;color:#1d4ed8;">{stats["nigeria_new"]} new &nbsp;·&nbsp; {stats["nigeria_total"]} total</td>
        </tr>
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;color:#374151;">🌍 International tab</td>
          <td style="padding:10px 16px;border-bottom:1px solid #e5e7eb;font-weight:700;color:#1d4ed8;">{stats["intl_new"]} new &nbsp;·&nbsp; {stats["intl_total"]} total</td>
        </tr>
        <tr style="background:#f9fafb;">
          <td style="padding:10px 16px;color:#374151;">👥 Active subscribers</td>
          <td style="padding:10px 16px;font-weight:700;color:#15803d;">{stats["subscribers"]}</td>
        </tr>
        {bounce_row}
      </table>
    </td>
  </tr>

  <!-- Category breakdown -->
  <tr>
    <td style="padding:24px 32px 0;">
      <h2 style="margin:0 0 12px;font-size:1em;color:#374151;font-weight:700;">New entries by category</h2>
      <table style="border-collapse:collapse;">
        {_category_rows(stats["categories_new"])}
      </table>
    </td>
  </tr>

  <!-- Actions -->
  <tr>
    <td style="padding:24px 32px;">
      <table cellpadding="0" cellspacing="0">
        <tr>
          <td style="padding-right:12px;">
            <a href="{sheet_url}" style="display:inline-block;background:#1d4ed8;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-size:0.9em;font-weight:600;">View Google Sheet →</a>
          </td>
          <td>
            <a href="{actions_url}" style="display:inline-block;background:#374151;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-size:0.9em;font-weight:600;">View Actions →</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr style="background:#f9fafb;">
    <td style="padding:16px 32px;border-top:1px solid #e5e7eb;">
      <p style="margin:0;font-size:0.8em;color:#9ca3af;">
        ScoutBot Admin Report — generated automatically on the 1st of each month.<br>
        Sent to {ADMIN_EMAIL} only.
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>
"""


# ── Send ─────────────────────────────────────────────────────────────────────

def send_admin_report(stats: dict) -> None:
    html = build_email_html(stats)
    subject = f"ScoutBot Admin — {stats['report_date']} Monthly Report"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"ScoutBot Admin <{SENDER_EMAIL}>"
    msg["To"]      = ADMIN_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        s.sendmail(SENDER_EMAIL, [ADMIN_EMAIL], msg.as_string())

    logger.info(f"admin_report: Monthly report sent to {ADMIN_EMAIL} — {stats['report_date']}")


# ── Entry point ───────────────────────────────────────────────────────────────

def run_admin_report(window_days: int = 30) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger.info("admin_report: Collecting monthly stats...")
    stats = collect_stats(window_days=window_days)
    logger.info(
        f"admin_report: nigeria_new={stats['nigeria_new']} intl_new={stats['intl_new']} "
        f"total_live={stats['total_live']} subscribers={stats['subscribers']} "
        f"bounced_new={stats['bounced_new']}"
    )
    send_admin_report(stats)


if __name__ == "__main__":
    run_admin_report()
