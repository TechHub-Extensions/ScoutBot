import requests
import time
import random
import logging
import sqlite3

# --- CONFIGURATION ---
BACKEND_URL = "http://localhost:3001"
CHECK_INTERVAL = 21600  # 6 hours
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_new_opportunities():
    """
    Fetches fresh opportunities from the Scrapy Interceptor Queue.
    """
    opportunities = []
    
    try:
        # Connect to the Scrapy interceptor DB
        conn = sqlite3.connect('whatsapp_queue.db')
        cursor = conn.cursor()

        # Grab up to 3 opportunities that haven't been sent yet
        cursor.execute("""
            SELECT id, title, link, deadline 
            FROM pending_broadcasts 
            WHERE status = 'unsent' 
            LIMIT 3
        """)
        rows = cursor.fetchall()

        for row in rows:
            opportunities.append({
                "id": row[0],
                "title": row[1],
                "link": row[2],
                "deadline": row[3]
            })

            # Mark as sent immediately so we don't spam them tomorrow!
            cursor.execute("UPDATE pending_broadcasts SET status = 'sent' WHERE id = ?", (row[0],))

        conn.commit()
        conn.close()

    except sqlite3.OperationalError as e:
        logging.error(f"⚠️ Interceptor DB unreachable. Handling silently. Details: {e}")
        return []
    except Exception as e:
        logging.error(f"⚠️ Unexpected error fetching Scrapy data: {e}")
        return []

    if opportunities:
        logging.info(f"📥 Successfully fetched {len(opportunities)} REAL opportunities from Scrapy.")
        
    return opportunities

def start_automation_loop():
    logging.info("🚀 ScoutBot Automation Daemon Started.")
    
    while True:
        logging.info("🔍 Checking for new opportunities...")
        
        try:
            groups_res = requests.get(f"{BACKEND_URL}/groups/export")
            groups = groups_res.json()
        except Exception as e:
            logging.error(f"Could not connect to Node backend: {e}")
            time.sleep(60)
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
                        res = requests.post(f"{BACKEND_URL}/send", json={
                            "group_jid": jid,
                            "message": msg
                        })
                        if res.status_code == 200:
                            logging.info(f"✅ Node backend confirmed send to {group['group_name']}")
                        else:
                            logging.error(f"❌ Node backend rejected payload: {res.text}")
                    except Exception as e:
                        logging.error(f"Failed to connect to Node: {e}")

                    # Anti-Ban Human Mimicry (15 to 30 seconds)
                    delay = random.uniform(15, 30)
                    logging.info(f"⏳ Sleeping for {int(delay)} seconds to mimic human typing...")
                    time.sleep(delay)

        logging.info(f"✅ Distribution cycle complete. Sleeping for {CHECK_INTERVAL/3600} hours.")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    start_automation_loop()