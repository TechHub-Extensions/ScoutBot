"""Clear all data rows from Nigeria and International tabs, keeping headers."""
import os, logging
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID       = os.getenv("SPREADSHEET_ID", "1pLCEvDI1btjtOe1H3VgzCqpC6R0nRsEtnTwQhY6BqmU")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
TAB_NAMES = ["Nigeria", "International"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def clear_tabs():
    import gspread
    from google.oauth2.service_account import Credentials

    json_path = SERVICE_ACCOUNT_JSON
    if not os.path.isabs(json_path):
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), json_path)

    creds = Credentials.from_service_account_file(json_path, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])
    client = gspread.authorize(creds)
    ss     = client.open_by_key(SPREADSHEET_ID)

    for tab_name in TAB_NAMES:
        try:
            ws   = ss.worksheet(tab_name)
            rows = ws.get_all_values()
            if len(rows) <= 1:
                logger.info("%s: already empty", tab_name)
                continue
            ws.delete_rows(2, len(rows))
            logger.info("%s: cleared %d rows", tab_name, len(rows) - 1)
        except Exception as exc:
            logger.error("%s: %s", tab_name, exc)


if __name__ == "__main__":
    clear_tabs()
