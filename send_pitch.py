"""
iléSure — Seed Funding Pitch Email Sender
Sends personalised cold emails to VC investors with the pitch deck attached.
Run: python send_pitch.py
"""

import smtplib
import time
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = "kamsirichard1960@gmail.com"
SENDER_APP_PASSWORD = "ogow lqzb ksti ebro"
SENDER_NAME = "Kamsi Richard"

PITCH_DECK_PATH = Path(__file__).parent.parent / "attached_assets" / "Ilesure_PitchDeck_2026_1781608707878.pptx"

# ---------------------------------------------------------------------------
# Full investor list — direct named contacts + fund inboxes
# ---------------------------------------------------------------------------
INVESTORS = [
    # Africa-focused VCs — direct decision-maker contacts
    {"name": "Maxime",      "email": "maxime@thecatalystfund.com",       "fund": "Catalyst Fund",         "focus": "africa"},
    {"name": "Maelis",      "email": "maelis@thecatalystfund.com",        "fund": "Catalyst Fund",         "focus": "africa"},
    {"name": "Ngetha",      "email": "ngetha@thecatalystfund.com",        "fund": "Catalyst Fund",         "focus": "africa"},
    {"name": "Dotun",       "email": "dolowoporoku@novastarventures.com", "fund": "Novastar Ventures",     "focus": "africa"},
    {"name": "Steve",       "email": "sbeck@novastarventures.com",        "fund": "Novastar Ventures",     "focus": "africa"},
    {"name": "Lavanya",     "email": "lavanya@vestedworld.com",           "fund": "VestedWorld",           "focus": "africa"},
    {"name": "Nneka",       "email": "nneka@vestedworld.com",             "fund": "VestedWorld",           "focus": "africa"},
    {"name": "Omobola",     "email": "omobola@tlcomcapital.com",          "fund": "TLcom Capital",         "focus": "africa"},
    {"name": "Andreata",    "email": "andreata@tlcomcapital.com",         "fund": "TLcom Capital",         "focus": "africa"},
    {"name": "Eloho",       "email": "eloho@tlcomcapital.com",            "fund": "TLcom Capital",         "focus": "africa"},
    {"name": "Maurizio",    "email": "maurizio@tlcomcapital.com",         "fund": "TLcom Capital",         "focus": "africa"},
    {"name": "Philippe",    "email": "philippe@tlcomcapital.com",         "fund": "TLcom Capital",         "focus": "africa"},
    {"name": "Cyril",       "email": "cyril@tlcomcapital.com",            "fund": "TLcom Capital",         "focus": "africa"},

    # US-based VCs — named partners
    {"name": "Marlon",      "email": "marlon@macventurecapital.com",      "fund": "MaC Venture Capital",   "focus": "us"},
    {"name": "Adrian",      "email": "adrian@macventurecapital.com",      "fund": "MaC Venture Capital",   "focus": "us"},
    {"name": "Walter",      "email": "walter@4dxventures.com",            "fund": "4DX Ventures",          "focus": "us"},
    {"name": "Peter",       "email": "peter@4dxventures.com",             "fund": "4DX Ventures",          "focus": "us"},
    {"name": "Robbie",      "email": "robbie@asymmetry.vc",               "fund": "Asymmetry Ventures",    "focus": "us"},
    {"name": "Jonathan",    "email": "jonathan@squarefoot.com",           "fund": "SquareFoot (Angel)",    "focus": "proptech"},

    # Europe / MENA — named partners
    {"name": "Mikael",      "email": "m@p1.ventures",                     "fund": "P1 Ventures",           "focus": "europe"},
    {"name": "Maria",       "email": "maria@p1.ventures",                 "fund": "P1 Ventures",           "focus": "africa"},
    {"name": "Shane",       "email": "shane@shorooq.com",                 "fund": "Shorooq Partners",      "focus": "europe"},
    {"name": "Mahmoud",     "email": "mahmoud@shorooq.com",               "fund": "Shorooq Partners",      "focus": "europe"},
    {"name": "Tarek",       "email": "tarek@endurecapital.com",           "fund": "Endure Capital",        "focus": "europe"},
    {"name": "Paras",       "email": "paras@e3-cap.com",                  "fund": "E3 Capital",            "focus": "europe"},
    {"name": "Vladimir",    "email": "vladimir@e3-cap.com",               "fund": "E3 Capital",            "focus": "europe"},
    {"name": "Hélène",      "email": "helene.demaegdt@gaia-impactfund.com","fund": "Gaia Impact Fund",     "focus": "europe"},
    {"name": "Guilhem",     "email": "guilhem.dupuy@gaia-impactfund.com", "fund": "Gaia Impact Fund",      "focus": "europe"},

    # Fund general inboxes
    {"name": "Team",        "email": "hello@thecatalystfund.com",         "fund": "Catalyst Fund",         "focus": "africa"},
    {"name": "Team",        "email": "info@novastarventures.com",         "fund": "Novastar Ventures",     "focus": "africa"},
    {"name": "Team",        "email": "info@vestedworld.com",              "fund": "VestedWorld",           "focus": "africa"},
    {"name": "Team",        "email": "hello@voltron.africa",              "fund": "Voltron Capital",       "focus": "africa"},
    {"name": "Team",        "email": "hello@hoaq.club",                   "fund": "HoaQ",                  "focus": "africa"},
    {"name": "Team",        "email": "info@macventurecapital.com",        "fund": "MaC Venture Capital",   "focus": "us"},
    {"name": "Team",        "email": "info@4dxventures.com",              "fund": "4DX Ventures",          "focus": "us"},
    {"name": "Team",        "email": "info@oystervc.com",                 "fund": "Oyster Ventures",       "focus": "proptech"},
    {"name": "Team",        "email": "info@asymmetry.vc",                 "fund": "Asymmetry Ventures",    "focus": "us"},
    {"name": "Team",        "email": "hello@endurecapital.com",           "fund": "Endure Capital",        "focus": "europe"},
    {"name": "Team",        "email": "info@kaleoventures.com",            "fund": "Kaleo Ventures",        "focus": "africa"},
    {"name": "Team",        "email": "info@goldenpalminvestments.com",    "fund": "Golden Palm Investments","focus": "africa"},
    {"name": "Team",        "email": "hello@remappedventures.com",        "fund": "Remapped Ventures",     "focus": "africa"},
    {"name": "Team",        "email": "founders@rebelfund.vc",             "fund": "Rebel Fund",            "focus": "us"},
    {"name": "Team",        "email": "info@hi2vc.com",                    "fund": "Hi2 Venture Fund",      "focus": "us"},
    {"name": "Team",        "email": "info@dcg.co",                       "fund": "Digital Currency Group","focus": "us"},
    {"name": "Team",        "email": "info@fastercapital.com",            "fund": "FasterCapital",         "focus": "europe"},
    {"name": "Team",        "email": "info@cvvc.com",                     "fund": "CV VC",                 "focus": "europe"},
    {"name": "Team",        "email": "finnfund@finnfund.fi",              "fund": "Finnfund",              "focus": "europe"},
    {"name": "Team",        "email": "info@proparco.fr",                  "fund": "Proparco",              "focus": "europe"},
    {"name": "Team",        "email": "contact@gaia-impactfund.com",       "fund": "Gaia Impact Fund",      "focus": "europe"},
    {"name": "Team",        "email": "info@e3-cap.com",                   "fund": "E3 Capital",            "focus": "europe"},
]


# ---------------------------------------------------------------------------
# Email body templates — Matías format (3-4 lines, hook, no fluff)
# ---------------------------------------------------------------------------

def build_email(investor: dict) -> tuple[str, str]:
    name = investor["name"]
    fund = investor["fund"]
    focus = investor["focus"]
    greeting = f"Hi {name}," if name != "Team" else f"Hi {fund} team,"

    if focus == "proptech":
        hook = (
            f"While billions are watching the World Cup this week, "
            f"275,000 Nigerians are trying to find a home — most of them paying ₦10,000 to a ghost agent and losing it."
        )
    elif focus == "africa":
        hook = (
            f"The World Cup has 5 billion eyes on North America right now. "
            f"Meanwhile, 275,000 Nigerians move to a new city every year and most lose money to ghost agents before they find a home."
        )
    elif focus == "us":
        hook = (
            f"Quick one while the World Cup is on — "
            f"275,000 students and NYSC corpers move to new Nigerian cities every year, and most get scammed paying inspection fees to strangers."
        )
    else:
        hook = (
            f"While the world watches the World Cup, Nigeria's housing market is running a fraud at scale — "
            f"275,000 people lose ₦10,000 to ghost agents every year, and no one has fixed it."
        )

    body = f"""{greeting}

{hook}

iléSure is fixing it — a verified housing directory with on-site property checks and escrow payments so money only moves when keys do. Alpha is live, ~100 organic signups, zero paid spend. We're raising $300K seed to launch beta in 4 months and own the Nigerian student-housing corridor.

Pitch deck is attached. Worth 5 minutes this week?

Kamsi Richard
Founder, iléSure
richardkamsiriochi@gmail.com | www.ilesure.com"""

    subject = f"Nigeria's housing fraud — $160M market, no one's fixed it yet | iléSure Seed"

    return subject, body


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def send_email(investor: dict, dry_run: bool = False) -> bool:
    subject, body = build_email(investor)
    to_email = investor["email"]

    msg = MIMEMultipart()
    msg["From"]    = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"]      = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    # Attach pitch deck
    if PITCH_DECK_PATH.exists():
        with open(PITCH_DECK_PATH, "rb") as f:
            part = MIMEBase("application", "vnd.openxmlformats-officedocument.presentationml.presentation")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename="iléSure_PitchDeck_2026.pptx",
        )
        msg.attach(part)

    if dry_run:
        print(f"[DRY RUN] Would send to {to_email} ({investor['fund']})")
        print(f"  Subject: {subject}")
        print(f"  Body preview: {body[:120].replace(chr(10), ' ')}")
        return True

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"✅  Sent  →  {to_email}  ({investor['fund']})")
        return True
    except Exception as e:
        print(f"❌  Failed  →  {to_email}  ({investor['fund']})  —  {e}")
        return False


def main():
    print(f"iléSure Pitch Campaign — {len(INVESTORS)} targets")
    print(f"Pitch deck: {'✅ found' if PITCH_DECK_PATH.exists() else '❌ NOT FOUND'}")
    print("=" * 60)

    sent = 0
    failed = 0
    seen_emails = set()

    for investor in INVESTORS:
        email = investor["email"].lower()
        if email in seen_emails:
            continue
        seen_emails.add(email)

        ok = send_email(investor)
        if ok:
            sent += 1
        else:
            failed += 1

        # Polite delay — avoids Gmail rate limiting
        time.sleep(3)

    print("=" * 60)
    print(f"Done — {sent} sent, {failed} failed")


if __name__ == "__main__":
    main()
