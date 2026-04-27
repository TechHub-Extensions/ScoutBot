"""
ScoutBot — curated startup funding seed.

Populates the Google Sheet with 60+ hand-verified startup funding opportunities
that are open globally — accelerators, VC funds, grants, incubators, and
fellowships. These are stable, recurring programs (most rolling/year-round),
so they will not be removed by the cleanup module.

This complements the dynamic spider, which adds time-bounded opportunities
discovered each run.

Run once to seed:
    python seed_funding.py

Safe to re-run: it skips any entry already in the sheet (matched by link).
"""

import os
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")

SHEET_HEADERS = [
    "Title", "Industry", "Category", "Range", "Education Level",
    "Organization", "Summary", "Application Link",
    "Opening Date", "Deadline", "Status",
]

# Each entry follows the same column order as the sheet.
# Range: "National" = Nigeria-focused / "International" = global or non-Nigerian.
# Education Level: "Any" — startup funding is open regardless of student status.
# Deadline: "Rolling" / "Annual" / "Ongoing" — never expire automatically.
SEED_FUNDING = [
    # ============================================================
    # AFRICAN / NIGERIAN STARTUP FUNDING
    # ============================================================
    ("Tony Elumelu Foundation Entrepreneurship Programme", "Startup", "Grant", "International", "Any",
     "Tony Elumelu Foundation",
     "$5,000 seed grant + 12-week training + mentorship for African entrepreneurs across all 54 African countries. One of the largest African entrepreneurship programs.",
     "https://www.tonyelumelufoundation.org/apply", "", "Annual", "Open"),

    ("GSMA Innovation Fund for Africa", "Startup", "Grant", "International", "Any",
     "GSMA",
     "Equity-free grants of £100k–£250k for African mobile-tech startups solving climate, agriculture, or digital-inclusion problems.",
     "https://www.gsma.com/mobilefordevelopment/m4dutilities/gsma-innovation-fund/", "", "Annual", "Open"),

    ("AfriLabs Catalyst Fund", "Startup", "Grant", "International", "Any",
     "AfriLabs",
     "Funding and capacity-building for African innovation hubs and startups across 50+ African countries.",
     "https://www.afrilabs.com/", "", "Rolling", "Open"),

    ("MEST Africa Entrepreneurship Programme", "Startup", "Accelerator", "International", "Any",
     "MEST Africa",
     "12-month fully funded entrepreneurship training + up to $100k seed for software startups led by Africans.",
     "https://meltwater.org/", "", "Annual", "Open"),

    ("Founder Institute Lagos", "Startup", "Accelerator", "National", "Any",
     "Founder Institute",
     "World's largest pre-seed startup accelerator with a Lagos chapter. 14-week structured program.",
     "https://fi.co/s/lagos", "", "Rolling", "Open"),

    ("CcHub Pitch Friday", "Startup", "Pitch Competition", "National", "Any",
     "Co-Creation Hub (CcHub)",
     "Monthly pitch event in Lagos for early-stage startups. Winners get investment, workspace, and mentorship.",
     "https://cchubnigeria.com/", "", "Monthly", "Open"),

    ("Ventures Platform Fund", "Startup", "VC Funding", "National", "Any",
     "Ventures Platform",
     "Pre-seed and seed-stage VC fund for African (especially Nigerian) tech startups. Cheque size $50k–$500k.",
     "https://venturesplatform.com/", "", "Rolling", "Open"),

    ("Microtraction", "Startup", "VC Funding", "National", "Any",
     "Microtraction",
     "Pre-seed VC for early African tech startups. Standard offer: $25k for 7% equity + follow-on support.",
     "https://microtraction.com/", "", "Rolling", "Open"),

    ("LoftyInc Afropreneurs Fund", "Startup", "VC Funding", "International", "Any",
     "LoftyInc Capital",
     "Africa-focused early-stage VC backing tech founders across Nigeria, Egypt, Kenya, and Francophone Africa.",
     "https://loftyincapital.com/", "", "Rolling", "Open"),

    ("EchoVC Partners", "Startup", "VC Funding", "International", "Any",
     "EchoVC",
     "Seed and early-stage VC investing in tech startups across Africa with a Nigerian base.",
     "https://www.echovc.com/", "", "Rolling", "Open"),

    ("Future Africa", "Startup", "VC Funding", "International", "Any",
     "Future Africa (Iyinoluwa Aboyeji)",
     "Mission-driven VC fund + syndicate backing African mission-driven founders building category-defining companies.",
     "https://future.africa/", "", "Rolling", "Open"),

    ("Catalyst Fund", "Startup", "Accelerator", "International", "Any",
     "BFA Global",
     "Inclusive-tech accelerator for emerging-market startups. $100k grant + 6-month venture-building support.",
     "https://bfaglobal.com/catalyst-fund/", "", "Rolling", "Open"),

    ("Norrsken22 African Tech Growth Fund", "Startup", "VC Funding", "International", "Any",
     "Norrsken22",
     "$200M growth fund backing Series A/B African tech startups in fintech, edtech, healthtech, and marketplaces.",
     "https://www.norrsken22.com/", "", "Rolling", "Open"),

    ("Norrsken Impact Accelerator", "Startup", "Accelerator", "International", "Any",
     "Norrsken Foundation",
     "$125k investment + 18-month mentorship for impact-driven startups. Stockholm-based, accepts global founders.",
     "https://www.norrsken.org/programs/impact-accelerator", "", "Annual", "Open"),

    ("Mastercard Foundation Young Africa Works", "Startup", "Grant", "International", "Any",
     "Mastercard Foundation",
     "Funding programs for African youth-led businesses across agriculture, tech, and creative industries.",
     "https://mastercardfdn.org/", "", "Rolling", "Open"),

    ("Africa's Business Heroes (Jack Ma Foundation)", "Startup", "Pitch Competition", "International", "Any",
     "Jack Ma Foundation",
     "Annual pan-African competition with $1.5M total prize pool for top 10 African entrepreneurs.",
     "https://africabusinessheroes.org/", "", "Annual", "Open"),

    ("Heifer AYUTE Africa Challenge", "Startup", "Pitch Competition", "International", "Any",
     "Heifer International",
     "$1.5M prize pool for African agri-tech startups solving smallholder-farmer challenges.",
     "https://www.heifer.org/ayute-africa.html", "", "Annual", "Open"),

    ("African Development Bank YouthADAPT Challenge", "Startup", "Grant", "International", "Any",
     "AfDB / Global Center on Adaptation",
     "Grants up to $100k for African youth-led businesses building climate-adaptation solutions.",
     "https://www.afdb.org/en/topics-and-sectors/initiatives-partnerships/youth-adapt", "", "Annual", "Open"),

    ("GreenTec Capital Africa", "Startup", "VC Funding", "International", "Any",
     "GreenTec Capital",
     "Result-based investor in African startups; provides capital + operational support to scale to profitability.",
     "https://www.greentec-capital.com/", "", "Rolling", "Open"),

    ("Pangea Accelerator", "Startup", "Accelerator", "International", "Any",
     "Pangea Accelerator",
     "Pan-African accelerator for early-stage startups. Investor matchmaking + scale-up support.",
     "https://pangea.world/", "", "Rolling", "Open"),

    ("Partech Africa", "Startup", "VC Funding", "International", "Any",
     "Partech",
     "$300M Africa-focused VC fund investing $1M–$15M in growth-stage African tech startups.",
     "https://partechpartners.com/africa/", "", "Rolling", "Open"),

    ("TLcom Capital TIDE Africa Fund", "Startup", "VC Funding", "International", "Any",
     "TLcom Capital",
     "$150M+ Africa-focused VC; Seed–Series B investments in African tech startups (Andela, Twiga, uLesson).",
     "https://www.tlcomcapital.com/", "", "Rolling", "Open"),

    ("4DX Ventures", "Startup", "VC Funding", "International", "Any",
     "4DX Ventures",
     "Early-stage Africa-focused VC backing seed and pre-Series A tech founders across the continent.",
     "https://www.4dxventures.com/", "", "Rolling", "Open"),

    ("Quona Capital", "Startup", "VC Funding", "International", "Any",
     "Quona Capital",
     "Emerging-markets fintech VC with a strong Africa focus. Cheque size $1M–$10M.",
     "https://quona.com/", "", "Rolling", "Open"),

    ("P1 Ventures", "Startup", "VC Funding", "International", "Any",
     "P1 Ventures",
     "Early-stage pan-African VC investing in pre-seed and seed-stage tech startups.",
     "https://www.p1ventures.com/", "", "Rolling", "Open"),

    ("Atlantica Ventures", "Startup", "VC Funding", "International", "Any",
     "Atlantica Ventures",
     "Sector-agnostic African VC investing in seed and Series A tech startups.",
     "https://atlantica.vc/", "", "Rolling", "Open"),

    # ============================================================
    # GLOBAL ACCELERATORS — North America / Global
    # ============================================================
    ("Y Combinator", "Startup", "Accelerator", "International", "Any",
     "Y Combinator",
     "World's most prestigious startup accelerator. $500k investment for 7% equity + 3 months in Silicon Valley. Two batches per year.",
     "https://www.ycombinator.com/apply", "", "Bi-annual", "Open"),

    ("Techstars", "Startup", "Accelerator", "International", "Any",
     "Techstars",
     "Global 3-month accelerator across 30+ cities. $120k investment + mentor network for early-stage startups.",
     "https://www.techstars.com/apply", "", "Rolling", "Open"),

    ("500 Global", "Startup", "VC Funding", "International", "Any",
     "500 Global (500 Startups)",
     "Early-stage VC and accelerator with a global portfolio of 2,800+ companies in 80+ countries.",
     "https://500.co/", "", "Rolling", "Open"),

    ("Plug and Play Tech Center", "Startup", "Accelerator", "International", "Any",
     "Plug and Play",
     "Industry-specific accelerator (Fintech, PropTech, Mobility, Health) with offices in 30+ countries.",
     "https://www.plugandplaytechcenter.com/", "", "Rolling", "Open"),

    ("Antler", "Startup", "Accelerator", "International", "Any",
     "Antler",
     "Day-zero global VC + 6-month founder-residency program in 30+ cities including London, Singapore, Nairobi, Sydney.",
     "https://www.antler.co/apply", "", "Rolling", "Open"),

    ("MassChallenge", "Startup", "Accelerator", "International", "Any",
     "MassChallenge",
     "Equity-free 4-month accelerator with $2M+ in cash prizes. Operates in USA, UK, Israel, Mexico, and Switzerland.",
     "https://masschallenge.org/apply", "", "Annual", "Open"),

    ("Startupbootcamp", "Startup", "Accelerator", "International", "Any",
     "Startupbootcamp",
     "Global accelerator with vertical programs (FinTech, Smart City, Energy) across Europe, Asia, and Africa.",
     "https://www.startupbootcamp.org/", "", "Rolling", "Open"),

    # ============================================================
    # GLOBAL ACCELERATORS — Europe
    # ============================================================
    ("Seedcamp", "Startup", "VC Funding", "International", "Any",
     "Seedcamp",
     "London-based pre-seed and seed VC investing in European founders. Portfolio includes Revolut, TransferWise, UiPath.",
     "https://seedcamp.com/", "", "Rolling", "Open"),

    ("Founders Factory", "Startup", "Accelerator", "International", "Any",
     "Founders Factory",
     "London-based corporate accelerator + studio. Pre-seed funding + 6-month program; includes an Africa branch in Johannesburg.",
     "https://foundersfactory.com/", "", "Rolling", "Open"),

    ("Entrepreneur First (EF)", "Startup", "Accelerator", "International", "Any",
     "Entrepreneur First",
     "Talent-investor: backs individuals before they have a company. Programs in London, Bangalore, Singapore, Berlin, Toronto.",
     "https://www.joinef.com/apply/", "", "Rolling", "Open"),

    ("Station F Founders Program", "Startup", "Incubator", "International", "Any",
     "Station F (Paris)",
     "World's largest startup campus in Paris. Free founders program + access to 30+ investor and corporate programs.",
     "https://stationf.co/programs", "", "Rolling", "Open"),

    ("Endeavor", "Startup", "Accelerator", "International", "Any",
     "Endeavor Global",
     "Selects high-impact entrepreneurs in 40+ countries (incl. Nigeria) and connects them to mentors, capital, and global networks.",
     "https://endeavor.org/", "", "Rolling", "Open"),

    ("EIT Digital Accelerator", "Startup", "Accelerator", "International", "Any",
     "EIT Digital (EU)",
     "European Union-backed accelerator helping deep-tech scale-ups expand internationally.",
     "https://eitdigitalaccelerator.com/", "", "Rolling", "Open"),

    # ============================================================
    # GLOBAL ACCELERATORS — Asia / Pacific
    # ============================================================
    ("Surge by Sequoia (Peak XV Partners)", "Startup", "Accelerator", "International", "Any",
     "Peak XV Partners",
     "Rapid scale-up program for India and Southeast Asia early-stage startups. $1M-$3M investment per company.",
     "https://www.peakxv.com/surge", "", "Bi-annual", "Open"),

    ("Antler Singapore", "Startup", "Accelerator", "International", "Any",
     "Antler",
     "Day-zero residency for founders in Singapore. Open to international applicants. Pre-seed funding offered.",
     "https://www.antler.co/locations/singapore", "", "Rolling", "Open"),

    ("Iterative (Southeast Asia)", "Startup", "Accelerator", "International", "Any",
     "Iterative",
     "YC-style accelerator for Southeast Asian founders. $500k investment + intensive 3-month program.",
     "https://iterative.vc/", "", "Bi-annual", "Open"),

    ("SOSV (HAX, IndieBio, Orbit Startups)", "Startup", "Accelerator", "International", "Any",
     "SOSV",
     "Multi-stage VC + global accelerators for hardware (HAX), biotech (IndieBio), and emerging-market software.",
     "https://sosv.com/", "", "Rolling", "Open"),

    ("Startmate Accelerator (Australia / NZ)", "Startup", "Accelerator", "International", "Any",
     "Startmate",
     "Leading Australia & New Zealand startup accelerator. $120k AUD investment + 5-month program.",
     "https://www.startmate.com/apply", "", "Bi-annual", "Open"),

    ("Blackbird Ventures (AU/NZ)", "Startup", "VC Funding", "International", "Any",
     "Blackbird",
     "Largest venture capital firm in Australia and New Zealand. Backs ambitious tech founders globally.",
     "https://www.blackbird.vc/", "", "Rolling", "Open"),

    # ============================================================
    # FELLOWSHIPS & STUDENT-FOUNDER FUNDING
    # ============================================================
    ("Thiel Fellowship", "Startup", "Fellowship", "International", "Any",
     "Thiel Foundation",
     "$200,000 over 2 years for under-22 founders willing to skip or stop college and build something new.",
     "https://thielfellowship.org/", "", "Annual", "Open"),

    ("On Deck Founders Program", "Startup", "Fellowship", "International", "Any",
     "On Deck",
     "Community-driven fellowship for prospective founders. Cohort-based program with thousands of alumni founders.",
     "https://www.beondeck.com/", "", "Rolling", "Open"),

    ("Pioneer.app", "Startup", "Grant", "International", "Any",
     "Pioneer",
     "Tournament-style program: weekly progress challenges, $100k prize + Silicon Valley flight for top performers.",
     "https://pioneer.app/", "", "Rolling", "Open"),

    ("Emergent Ventures (Mercatus Center)", "Startup", "Grant", "International", "Any",
     "Mercatus Center / Tyler Cowen",
     "Discretionary grants ($5k–$100k+) for founders, researchers, and creators with breakthrough ideas worldwide.",
     "https://www.mercatus.org/emergent-ventures", "", "Rolling", "Open"),

    ("Z Fellows", "Startup", "Fellowship", "International", "Any",
     "Z Fellows",
     "1-week intensive program in San Francisco. $10k investment + lifetime founder community access.",
     "https://www.zfellows.com/", "", "Rolling", "Open"),

    ("South Park Commons Founder Fellowship", "Startup", "Fellowship", "International", "Any",
     "South Park Commons",
     "$400k investment + 6 months in San Francisco for founders exploring 0-to-1 ideas.",
     "https://www.southparkcommons.com/founder-fellowship", "", "Rolling", "Open"),

    # ============================================================
    # CORPORATE & PLATFORM PROGRAMS — credits, grants, perks
    # ============================================================
    ("Microsoft for Startups Founders Hub", "Startup", "Grant", "International", "Any",
     "Microsoft",
     "Up to $150,000 in Azure credits + free OpenAI / GitHub / Office tools for any qualifying startup. No equity, no fees.",
     "https://www.microsoft.com/en-us/startups", "", "Rolling", "Open"),

    ("Google for Startups Accelerator (Africa)", "Startup", "Accelerator", "International", "Any",
     "Google for Startups",
     "3-month equity-free accelerator for African Seed–Series A startups. Mentorship + Google product credits.",
     "https://startup.google.com/accelerator/africa/", "", "Annual", "Open"),

    ("Google for Startups Black Founders Fund (Africa)", "Startup", "Grant", "International", "Any",
     "Google for Startups",
     "Up to $150,000 non-dilutive funding + Google Cloud credits for Black-led African startups.",
     "https://startup.google.com/programs/black-founders-fund/africa/", "", "Annual", "Open"),

    ("AWS Activate", "Startup", "Grant", "International", "Any",
     "Amazon Web Services",
     "Up to $100,000 in AWS credits + technical support + business mentorship for startups.",
     "https://aws.amazon.com/activate/", "", "Rolling", "Open"),

    ("NVIDIA Inception", "Startup", "Grant", "International", "Any",
     "NVIDIA",
     "Free program for AI/data-science startups: cloud credits, hardware discounts, marketing support, investor intros.",
     "https://www.nvidia.com/en-us/startups/", "", "Rolling", "Open"),

    ("OpenAI Startup Fund", "Startup", "VC Funding", "International", "Any",
     "OpenAI",
     "Investments in early-stage AI-native startups + $1M+ in OpenAI credits and Azure compute.",
     "https://openai.com/blog/openai-startup-fund", "", "Rolling", "Open"),

    ("Stripe Atlas", "Startup", "Incubator", "International", "Any",
     "Stripe",
     "Tools and US Delaware C-corp incorporation for global founders + access to the Atlas community.",
     "https://stripe.com/atlas", "", "Rolling", "Open"),

    ("HubSpot for Startups", "Startup", "Grant", "International", "Any",
     "HubSpot",
     "Up to 90% off HubSpot software for first year + free CRM tools for startups raising under $10M.",
     "https://www.hubspot.com/startups", "", "Rolling", "Open"),

    ("Notion for Startups", "Startup", "Grant", "International", "Any",
     "Notion",
     "$1,000+ in free Notion Plus credits + AI features for early-stage startups.",
     "https://www.notion.so/startups", "", "Rolling", "Open"),

    ("Mozilla Builders", "Startup", "Grant", "International", "Any",
     "Mozilla",
     "Up to $100k grants + Mozilla mentorship for early-stage AI and open-source projects.",
     "https://builders.mozilla.org/", "", "Rolling", "Open"),

    # ============================================================
    # IMPACT / SOCIAL VENTURE
    # ============================================================
    ("Echoing Green Fellowship", "Startup", "Fellowship", "International", "Any",
     "Echoing Green",
     "$80,000–$90,000 stipend over 2 years + leadership development for social entrepreneurs starting impact ventures.",
     "https://echoinggreen.org/fellowship/", "", "Annual", "Open"),

    ("Skoll Awards for Social Entrepreneurship", "Startup", "Award", "International", "Any",
     "Skoll Foundation",
     "$2M unrestricted funding awarded to proven social entrepreneurs driving large-scale change.",
     "https://skoll.org/about/skoll-awards/", "", "Annual", "Open"),

    ("Acumen Fellowship", "Startup", "Fellowship", "International", "Any",
     "Acumen",
     "Year-long fellowship for emerging social-impact leaders in East Africa, West Africa, India, Pakistan, and more.",
     "https://acumenacademy.org/", "", "Annual", "Open"),

    ("Ashoka Fellowship", "Startup", "Fellowship", "International", "Any",
     "Ashoka",
     "Lifetime support, stipend, and a global network for system-changing social entrepreneurs.",
     "https://www.ashoka.org/en/program/ashoka-fellowship", "", "Rolling", "Open"),

    ("Rolex Awards for Enterprise", "Startup", "Award", "International", "Any",
     "Rolex",
     "CHF 200,000 (~$220k) for visionaries driving projects that improve life on Earth.",
     "https://www.rolex.org/rolex-awards", "", "Bi-annual", "Open"),

    # ============================================================
    # PROPTECH / HOUSING / REAL ESTATE — relevant to Ile Sure
    # ============================================================
    ("MetaProp NYC PropTech Accelerator", "Startup", "Accelerator", "International", "Any",
     "MetaProp",
     "World's leading PropTech accelerator. 22-week program in NYC + investment for real-estate technology startups.",
     "https://www.metaprop.com/accelerator", "", "Annual", "Open"),

    ("Pi Labs (Property Innovation Labs)", "Startup", "VC Funding", "International", "Any",
     "Pi Labs",
     "Europe's first PropTech-focused VC. Early-stage investment + accelerator program for property-tech startups.",
     "https://pilabs.co.uk/", "", "Rolling", "Open"),

    ("Plug and Play Real Estate & Construction", "Startup", "Accelerator", "International", "Any",
     "Plug and Play",
     "Industry-specific PropTech and ConTech accelerator with 100+ corporate partners.",
     "https://www.plugandplaytechcenter.com/real-estate/", "", "Rolling", "Open"),

    # ============================================================
    # NIGERIAN GOVERNMENT / ECOSYSTEM PROGRAMS
    # ============================================================
    ("NITDA Tech Talent Accelerator", "Startup", "Grant", "National", "Any",
     "National Information Technology Development Agency (NITDA)",
     "Federal Nigerian government grants and accelerator for indigenous tech startups and innovators.",
     "https://nitda.gov.ng/", "", "Rolling", "Open"),

    ("Bank of Industry (BOI) Youth Entrepreneurship Support", "Startup", "Grant", "National", "Any",
     "Bank of Industry Nigeria",
     "Single-digit-interest loans + business training for Nigerian youth-led startups (18–35 yrs).",
     "https://www.boi.ng/yes-programme/", "", "Rolling", "Open"),

    ("CBN AGSMEIS Loan", "Startup", "Grant", "National", "Any",
     "Central Bank of Nigeria",
     "Up to ₦10M loan at 5% interest for Nigerian SME and startup founders. Equity & training combined.",
     "https://www.cbn.gov.ng/", "", "Rolling", "Open"),
]


def seed():
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        json_path = SERVICE_ACCOUNT_JSON
        if not os.path.isabs(json_path):
            json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), json_path)

        creds = Credentials.from_service_account_file(json_path, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1

        all_values = sheet.get_all_values()
        if not all_values:
            sheet.append_row(SHEET_HEADERS)
            existing_links = set()
        else:
            existing_links = {row[7].strip() for row in all_values[1:] if len(row) > 7 and row[7].strip()}

        new_rows = []
        for entry in SEED_FUNDING:
            link = entry[7]
            if link not in existing_links:
                new_rows.append(list(entry))
                existing_links.add(link)

        if not new_rows:
            logger.info(f"seed_funding: All {len(SEED_FUNDING)} entries already in sheet — nothing to add.")
            return 0

        sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
        logger.info(f"seed_funding: Added {len(new_rows)} new startup funding opportunities to the sheet.")
        return len(new_rows)

    except Exception as exc:
        logger.error(f"seed_funding: Failed — {exc}")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    seed()
