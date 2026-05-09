import requests
import time
import random
import logging
from datetime import datetime

# --- CONFIGURATION ---
BACKEND_URL = "http://localhost:3001"
# How often to check for new data (in seconds). e.g., 21600 = 6 hours
CHECK_INTERVAL = 21600 
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_new_opportunities():
    """
    In the future, this will fetch from your Scrapy database.
    For now, we return a structured payload.
    """
    return [
        {
            "id": "intern_001",
            "title": "Goldman Sachs 2026 Engineering Internship",
            "link": "https://goldmansachs.com/careers",
            "deadline": "Oct 31, 2025"
        }
    ]

def start_automation_loop():
    logging.info("🚀 ScoutBot Automation Daemon Started.")
    
    while True:
        logging.info("🔍 Checking for new opportunities...")
        
        # 1. Fetch active groups from the Node backend
        try:
            groups_res = requests.get(f"{BACKEND_URL}/groups/export")
            groups = groups_res.json()
        except Exception as e:
            logging.error(f"Could not connect to Node backend: {e}")
            time.sleep(60) # Wait a minute and retry
            continue

        if not groups:
            logging.warning("No active groups found. Sleeping...")
        else:
            opportunities = get_new_opportunities()
            
            for opp in opportunities:
                # Build professional WhatsApp Markdown
                msg = (
                    f"✨ *NEW OPPORTUNITY* ✨\n\n"
                    f"📌 *{opp['title']}*\n"
                    f"📅 Deadline: {opp['deadline']}\n\n"
                    f"🔗 Apply Here: {opp['link']}\n\n"
                    f"_Powered by ScoutBot x Cowrywise_"
                )

                for group in groups:
                    jid = group['group_jid']
                    logging.info(f"Distributing to {group['group_name']}...")
                    
                    try:
                        requests.post(f"{BACKEND_URL}/send", json={
                            "group_jid": jid,
                            "message": msg
                        })
                    except Exception as e:
                        logging.error(f"Failed to send to {jid}: {e}")

                    # Anti-Ban Human Mimicry
                    time.sleep(random.uniform(5, 12))

        logging.info(f"✅ Distribution cycle complete. Sleeping for {CHECK_INTERVAL/3600} hours.")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    start_automation_loop()