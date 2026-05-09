import requests
import time
import random

BACKEND_URL = "http://localhost:3001"

def fire_test_broadcast():
    print("🚀 Fetching registered groups from ScoutBot API...")
    try:
        response = requests.get(f"{BACKEND_URL}/groups/export")
        groups = response.json()
    except Exception as e:
        print(f"❌ Failed to connect to Node backend: {e}")
        return

    if not groups:
        print("⚠️ No active groups found in the database. Register one first!")
        return

    print(f"✅ Found {len(groups)} active group(s). Preparing payload...\n")

    # The payload formatted with WhatsApp Markdown (Bold, Italics, Emojis)
    test_message = (
        "🚨 *ScoutBot Network: Test Broadcast* 🚨\n\n"
        "Hello from the ScoutBot Distribution Engine! 🤖💙\n"
        "If you are seeing this, the bridge between our scraper and this WhatsApp group is fully operational.\n\n"
        "_Prepare for premium internships, scholarships, and fellowships. Build in public._ 🚀"
    )

    for group in groups:
        jid = group['group_jid']
        name = group['group_name']

        print(f"📡 Firing payload to: {name}...")

        payload = {
            "group_jid": jid,
            "message": test_message
        }

        try:
            res = requests.post(f"{BACKEND_URL}/send", json=payload)
            if res.status_code == 200:
                print(f"✅ Success: Dropped in {name}")
            else:
                print(f"❌ Server rejected payload for {name}: {res.text}")
        except Exception as e:
            print(f"❌ Error reaching API for {name}: {e}")

        # The Golden Anti-Ban Rule: Random Delay between 3 and 8 seconds
        delay = random.uniform(15, 30)
        print(f"⏳ Sleeping for {delay:.2f}s to mimic human behavior...\n")
        time.sleep(delay)
        # Wait between 15 and 30 seconds before sending the next opportunity to avoid triggering WhatsApp's anti-spam filters. This mimics the natural delay of a human sharing opportunities and reduces the risk of bans.

    print("🎉 All test broadcasts completed successfully!")

if __name__ == "__main__":
    fire_test_broadcast()