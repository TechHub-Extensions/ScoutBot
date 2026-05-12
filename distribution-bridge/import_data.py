import sqlite3
import json
import os

# 🚨 UPDATED: Dynamic paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'whatsapp_queue.db')
JSON_PATH = os.path.join(BASE_DIR, 'opportunities.json')

def import_data():
    if not os.path.exists(JSON_PATH):
        print(f"❌ Error: Could not find {JSON_PATH}")
        return

    # 1. Connect to the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. Build the table the daemon expects
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')

    # 3. Read the JSON file
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        opportunities = json.load(f)

    # 4. Insert the data into the database
    count = 0
    for opp in opportunities:
        title = opp.get('title', 'Untitled Opportunity')
        # Handle the link whether your JSON calls it 'application_link' or 'link'
        link = opp.get('application_link') or opp.get('link') or '#'
        deadline = opp.get('deadline', '2026-12-31') 

        cursor.execute('''
            INSERT INTO pending_broadcasts (title, link, deadline)
            VALUES (?, ?, ?)
        ''', (title, link, deadline))
        count += 1

    conn.commit()
    conn.close()
    print(f"✅ SUCCESS! Loaded {count} opportunities into {DB_PATH}")

if __name__ == "__main__":
    import_data()