import requests
import time
import random
import logging
import sqlite3

# --- CONFIGURATION ---
BACKEND_URL = "http://localhost:3001"
CHECK_INTERVAL = 12600  # 3.5 hours
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_unseen_opportunities(group_jid):
    """
    Fetches up to 3 fresh, unexpired opportunities that a SPECIFIC group has never seen.
    """
    opportunities = []
    
    try:
        # Connect to the Scrapy interceptor DB
        conn = sqlite3.connect('whatsapp_queue.db')
        
        # 🚨 UPDATED: Attach the Node database to cross-reference what this group has seen
        conn.execute("ATTACH DATABASE 'scoutbot.db' AS scoutdb")
        cursor = conn.cursor()

        # 🚨 UPDATED: Grab 3 unseen, active opportunities
        cursor.execute("""
            SELECT id, title, link, deadline 
            FROM pending_broadcasts 
            WHERE deadline > DATE('now')
            AND id NOT IN (
                SELECT opportunity_title FROM scoutdb.broadcast_log WHERE group_jid = ?
            )
            ORDER BY RANDOM() 
            LIMIT 3
        """, (group_jid,))
        
        rows = cursor.fetchall()

        for row in rows:
            opportunities.append({
                "id": row[0],
                "title": row[1],
                "link": row[2],
                "deadline": row[3]
            })

        # Notice: We removed the UPDATE status = 'sent' here to keep them in the global pool
        conn.close()

    except sqlite3.OperationalError as e:
        logging.error(f"⚠️ Interceptor DB unreachable. Handling silently. Details: {e}")
        return []
    except Exception as e:
        logging.error(f"⚠️ Unexpected error fetching Scrapy data: {e}")
        return []

    return opportunities

def start_automation_loop():
    logging.info("🚀 ScoutBot Automation Daemon Started.")
    
    while True:
        logging.info("🔍 Checking for new opportunities...")
        
        # 🚨 CRITICAL FIX 1: Health-Check Ping (Ghost Disconnect Protection)
        try:
            status_res = requests.get(f"{BACKEND_URL}/status").json()
            if not status_res.get("ready"):
                logging.warning("CRITICAL: WhatsApp is disconnected. Pausing for 30 mins...")
                time.sleep(1800)
                continue # Skip this run to prevent a total crash
        except Exception as e:
            logging.error(f"Node backend offline: {e}. Pausing for 30 mins...")
            time.sleep(1800)
            continue

        try:
            groups_res = requests.get(f"{BACKEND_URL}/groups/export")
            groups = groups_res.json()
        except Exception as e:
            logging.error(f"Could not fetch groups from Node: {e}")
            time.sleep(60)
            continue

        if not groups:
            logging.warning("No active groups found. Sleeping...")
        else:
            # Matrix rotation: Shuffle groups so the same campus doesn't always get texted first
            random.shuffle(groups)

            # 🚨 CRITICAL FIX 2: The Batch Drip Algorithm (Group-First Loop)
            for group_index, group in enumerate(groups):
                jid = group['group_jid']
                
                # Ask the DB for links strictly for this campus
                opportunities = get_unseen_opportunities(jid)
                
                if not opportunities:
                    logging.info(f"⏭️ {group['group_name']} has seen everything active. Skipping...")
                    continue
                    
                logging.info(f"Distributing {len(opportunities)} links to {group['group_name']}...")
                
                for opp in opportunities:
                    # 🚨 TRADEMARK FIX: Clean ScoutBot signature
                    msg = (
                        f"✨ *NEW OPPORTUNITY* ✨\n\n"
                        f"📌 *{opp['title']}*\n"
                        f"📅 Deadline: {opp['deadline']}\n\n"
                        f"🔗 Apply Here: {opp['link']}\n\n"
                        f"🤖_Powered by ScoutBot_"
                    )
                    
                    try:
                        res = requests.post(f"{BACKEND_URL}/send", json={
                            "group_jid": jid,
                            "message": msg
                        })
                        if res.status_code == 200:
                            logging.info(f"✅ Node backend confirmed send to {group['group_name']}")
                            
                            # Log the exact ID into scoutbot.db so it's never sent to this group again
                            log_conn = sqlite3.connect('scoutbot.db')
                            log_conn.execute(
                                "INSERT INTO broadcast_log (group_jid, opportunity_title, status) VALUES (?, ?, ?)",
                                (jid, str(opp['id']), 'sent')
                            )
                            log_conn.commit()
                            log_conn.close()
                        else:
                            logging.error(f"❌ Node backend rejected payload: {res.text}")
                    except Exception as e:
                        logging.error(f"Failed to connect to Node: {e}")

                    # Anti-Ban Human Mimicry (15 to 30 seconds between individual links)
                    delay = random.uniform(15, 30)
                    logging.info(f"⏳ Sleeping for {int(delay)} seconds to mimic human typing...")
                    time.sleep(delay)
                    
                # 🚨 CRITICAL FIX 3: The 30-60 Minute Coffee Break
                # Only take a coffee break if this isn't the final group in the list
                if group_index < len(groups) - 1:
                    coffee_break = random.uniform(1800, 3600) # 30 to 60 minutes
                    logging.info(f"☕ Taking a coffee break for {int(coffee_break/60)} minutes before the next campus...")
                    time.sleep(coffee_break)

        logging.info(f"✅ Distribution cycle complete. Sleeping for {CHECK_INTERVAL/3600} hours.")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    start_automation_loop()