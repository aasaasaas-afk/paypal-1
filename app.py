import asyncio
import time
import json
import logging
import threading
import os
from flask import Flask, jsonify
from pyrogram import Client

# ─── CONFIGURATION ───
API_ID = 39761812
API_HASH = "08eb23e7f0599533829fbd4b6f2d8eb5"
SESSION_STRING = "AQJQHbUAVozpsy2SLcoBegHKFdc1a2xG44y36_ZU9-E-bQ2q1cGe2G_bH4DtmFskTn0wu8iOuNAoyrtcwKGW-_iY1CIVgjvT3QDZoOqCpg1LEy4YbyVb3E8Bf-Hzk5nHpWshKtWGSgLeBe5qx-oTEPOkZ-nDjiDMkenP7pbWT5znX_Z0q_c98Z2pYHFtqGvbLGG16tgwhSiT7JvvkSJUbXo56RgjnZEJb_UTLR1w24V0VW6moHUuS5pEzAmJPkn-tesvjk7I9mE-q_dWxqxz0PQpcPqGzUlgXt3YIL_l59PwlLsuNjP-2-F3v7iARnbNTHWDLuh5iHaDDGrKxocx_bD18w2nhgAAAAHraX5JAA"

TARGET_BOT = "@newpayubot"

# ─── FLASK APP SETUP ───
app = Flask(__name__)

# ─── LOGGING SETUP ───
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.CRITICAL)

# ─── ASYNCIO BACKGROUND LOOP SETUP ───
loop = asyncio.new_event_loop()

def run_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Start the background thread
t = threading.Thread(target=run_loop, daemon=True)
t.start()

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
        # Check if client is actually connected
        if not pyrogram_client.is_connected:
            logger.error("Client is NOT connected! Attempting reconnect...")
            await pyrogram_client.connect()
            
        logger.info(f"Sending /chk {cc_number} to {TARGET_BOT}...")
        
        # Send Command
        await pyrogram_client.send_message(TARGET_BOT, f"/chk {cc_number}")
        
        logger.info("Command sent. Waiting 5 seconds...")
        await asyncio.sleep(5)
        
        logger.info("Fetching chat history...")
        # Get History
        async for message in pyrogram_client.get_chat_history(TARGET_BOT, limit=1):
            full_text = message.text or ""
            
            # Extract "Response:" line
            extracted = "No response found"
            for line in full_text.splitlines():
                if line.strip().startswith("Response:"):
                    extracted = line.split("Response:", 1)[1].strip()
                    break
            
            logger.info(f"Raw Bot Response: {extracted}")
            return extracted
            
    except Exception as e:
        logger.error(f"Error in get_card_response: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return "Error fetching response"

# ─── FLASK ROUTES ───

@app.route('/gate=b3/cc/<path:cc_details>')
def check_gate_b3(cc_details):
    try:
        start_time = time.time()
        
        # Clean input
        if cc_details.startswith("="):
            cc_details = cc_details[1:]
            
        logger.info(f"--- New Request ---")
        logger.info(f"Card Details: {cc_details}")
        
        # Run the async function in the background loop
        # We use a timeout to prevent hanging
        future = asyncio.run_coroutine_threadsafe(get_card_response(cc_details), loop)
        raw_response = future.result(timeout=30) 
        
        # 2. Determine Status and Final Response Text
        final_response_text = raw_response
        status = "DECLINED"
        
        # Logic: "Too many purchase attempts..."
        if "Too many purchase attempts" in raw_response:
            final_response_text = "Server Overloaded please wait for few minutes......"
            status = "DECLINED"
            
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
        
        logger.info(f"Final Result: {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"SERVER ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# ─── MAIN EXECUTION ───

if __name__ == "__main__":
    # 1. Start Pyrogram SYNCHRONOUSLY in the loop before Flask starts.
    # This guarantees the app is ready.
    logger.info("🔌 Starting Pyrogram Client...")
    
    # We use run_coroutine_threadsafe + .result() to block execution until it connects
    start_future = asyncio.run_coroutine_threadsafe(pyrogram_client.start(), loop)
    
    try:
        start_future.result(timeout=30) # Wait up to 30s for connection
        logger.info("✅ Pyrogram Connected Successfully.")
        
        # Optional: Test a basic connection
        me_future = asyncio.run_coroutine_threadsafe(pyrogram_client.get_me(), loop)
        me = me_future.result(timeout=10)
        logger.info(f"🆔 Logged in as: {me.first_name} (ID: {me.id})")
        
    except Exception as e:
        logger.critical(f"❌ FAILED TO CONNECT TO TELEGRAM: {e}")
        logger.critical("The API will NOT start because the userbot is dead.")
        sys.exit(1)
    
    # 2. Start Flask
    port = int(os.environ.get("PORT", 5000))
    print("🚀 Starting Flask API...")
    app.run(host="0.0.0.0", port=port)
