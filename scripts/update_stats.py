"""
Reads live stats from Google Sheets and rewrites the <!-- stats start/end -->
block in README.md.  Intended to run inside GitHub Actions after each scrape.
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _sheet_client():
    import gspread
    from google.oauth2.service_account import Credentials

    sa_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", str(ROOT / "service_account.json"))
    creds = Credentials.from_service_account_file(
        sa_path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    return gspread.authorize(creds)


def count_subscribers(client, form_sheet_id, spreadsheet_id):
    seen = set()

    # Form responses (column 4 = email)
    try:
        ws = client.open_by_key(form_sheet_id).worksheets()[0]
        for v in ws.col_values(4)[1:]:
            v = v.strip().lower()
            if v and "@" in v:
                seen.add(v)
    except Exception as exc:
        print(f"warning: form sheet error — {exc}", file=sys.stderr)

    # Subscribers tab (column 2 = email, skip 2 header rows)
    try:
        ss = client.open_by_key(spreadsheet_id)
        try:
            ws = ss.worksheet("Subscribers")
            for v in ws.col_values(2)[2:]:
                v = v.strip().lower()
                if v and "@" in v:
                    seen.add(v)
        except Exception:
            pass
    except Exception as exc:
        print(f"warning: subscribers tab error — {exc}", file=sys.stderr)

    return len(seen)


def count_opportunities(client, spreadsheet_id):
    total = 0
    ss = client.open_by_key(spreadsheet_id)
    for tab in ("Nigeria", "International"):
        try:
            ws = ss.worksheet(tab)
            rows = ws.get_all_values()
            # subtract 1 header row; ignore completely empty rows
            data_rows = [r for r in rows[1:] if any(c.strip() for c in r)]
            total += len(data_rows)
        except Exception as exc:
            print(f"warning: could not count '{tab}' — {exc}", file=sys.stderr)
    return total


def update_readme(subscribers: int, opportunities: int, readme_path: Path):
    text = readme_path.read_text(encoding="utf-8")
    today = date.today().strftime("%b %d, %Y")
    new_block = (
        f"<!-- stats start -->\n"
        f"**{subscribers:,} subscribers · {opportunities:,}+ opportunities indexed · "
        f"30 sources** *(updated {today})*\n"
        f"<!-- stats end -->"
    )

    pattern = re.compile(
        r"<!-- stats start -->.*?<!-- stats end -->", re.DOTALL
    )
    if pattern.search(text):
        updated = pattern.sub(new_block, text)
    else:
        # Insert after the badge block (first blank line after badges)
        updated = text.replace(
            "\n---\n",
            f"\n{new_block}\n\n---\n",
            1,
        )

    readme_path.write_text(updated, encoding="utf-8")
    print(f"README updated: {subscribers} subscribers, {opportunities} opportunities.")


def main():
    form_sheet_id  = os.environ.get("FORM_SHEET_ID",  "1dFcnVvQjWkuYhN1rplICTY0j88KgvGqQ3FzYId2ru4s")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")

    client        = _sheet_client()
    subscribers   = count_subscribers(client, form_sheet_id, spreadsheet_id)
    opportunities = count_opportunities(client, spreadsheet_id)
    update_readme(subscribers, opportunities, ROOT / "README.md")


if __name__ == "__main__":
    main()
