import asyncio
import time
import json
import logging
import sys
from flask import Flask, jsonify
from pyrogram import Client

# ─── CONFIGURATION ───
API_ID = 39761812
API_HASH = "08eb23e7f0599533829fbd4b6f2d8eb5"
SESSION_STRING = "1AZWarzoBu4TaL8Ux0FB2mma1K3Z6q55TZE3cjmWZXM9zmDkoJ8qTm083X4ZIfeXwygA8v9jWBkDfJs6Jf0wUDBYL7ptepjJaG_-HKyhdv330oNRlpwQz-RjwrQ5ApyscERS1i2QeX046QhsUk7W3CJ4qRFNs8hv-c6R9TugeM5ZSbAEKZ5JPiDRyd_qW2SE_4YjhnDnnftS0h8-DeAKL0NKuaWzwLKXrlvHMPk4sjl890lglNRDBUagtw9aMB_6NvuFQKhRHB2OzNN7pGJbDdDZmVCsaHKm_KzqPCS65aPqN3rTbcaPVbo-FoDynhUCLW1ftonJrCAi7jJekVEtesmEmf8n2im4="

TARGET_BOT = "@newpayubot"

# ─── FLASK APP SETUP ───
app = Flask(__name__)

# ─── LOGGING SETUP (Suppress Peer Errors) ───
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.CRITICAL)

def handle_exception(loop, context):
    exception = context.get('exception')
    if exception and "Peer id invalid" in str(exception):
        return
    loop.default_exception_handler(context)

# Initialize Pyrogram Client
pyrogram_client = Client(
    name="user_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    workers=1000
)

# ─── HELPER FUNCTIONS ───

async def get_card_response(cc_number):
    """
    Sends command to bot, waits 5s, fetches and parses response.
    """
    try:
        # Send Command
        await pyrogram_client.send_message(TARGET_BOT, f"/chk {cc_number}")
        
        # Wait 5 Seconds
        await asyncio.sleep(5)
        
        # Get History
        async for message in pyrogram_client.get_chat_history(TARGET_BOT, limit=1):
            full_text = message.text or ""
            
            # Extract "Response:" line
            extracted = "No response found"
            for line in full_text.splitlines():
                if line.strip().startswith("Response:"):
                    extracted = line.split("Response:", 1)[1].strip()
                    break
            return extracted
            
    except Exception as e:
        logger.error(f"Error getting response: {e}")
        return "Error fetching response"

# ─── FLASK ROUTES ───

@app.route('/gate=b3/cc/<cc_details>')
async def check_gate_b3(cc_details):
    start_time = time.time()
    
    # 1. Get the raw response from the bot
    raw_response = await get_card_response(cc_details)
    
    # 2. Determine Status and Final Response Text
    final_response_text = raw_response
    status = "DECLINED"
    
    # Logic: "Too many purchase attempts..."
    if "Too many purchase attempts" in raw_response:
        final_response_text = "Server Overloaded please wait for few minutes......"
        status = "DECLINED" # Or "ERROR", depending on preference. Using DECLINED as per "rest status"
        
    # Logic: "Card added"
    elif "Card added" in raw_response:
        status = "APPROVED"
        final_response_text = "Payment method added"
        
    # 3. Calculate Time
    end_time = time.time()
    duration = f"{end_time - start_time:.2f}s"
    
    # 4. Return JSON
    result = {
        "response": final_response_text,
        "status": status,
        "time": duration
    }
    
    return jsonify(result)

# ─── MAIN EXECUTION ───

if __name__ == "__main__":
    # Set global exception handler for asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(handle_exception)
    
    print("🔌 Starting Pyrogram Client...")
    # Start Pyrogram synchronously before running Flask
    # This ensures the user session is active when the first request comes in
    pyrogram_client.start()
    print("✅ Pyrogram Connected.")
    
    print("🚀 Starting Flask API on port 5000...")
    print("📡 Endpoint: /gate=b3/cc={cc|mm|yy|cvv}")
    
    try:
        # Run Flask
        app.run(host="0.0.0.0", port=5000)
    finally:
        print("🔌 Shutting down...")
        pyrogram_client.stop()
