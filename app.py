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

# ─── FLASK APP ───
app = Flask(__name__)

# ─── LOGGING ───
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.CRITICAL)

# ─── ASYNCIO BACKGROUND MANAGER ───
# We store the loop and client here. They will be initialized in the thread.
loop = None
pyrogram_client = None
startup_event = threading.Event()

def run_pyrogram_background():
    """
    This function runs in a separate thread.
    It creates its own Event Loop and Pyrogram Client.
    This prevents 'attached to a different loop' errors.
    """
    global loop, pyrogram_client
    
    # 1. Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    logger.info("Background thread: Loop created.")

    # 2. Instantiate the Client INSIDE this thread
    pyrogram_client = Client(
        name="user_session",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION_STRING,
        workers=1000
    )

    try:
        # 3. Start the client
        logger.info("Background thread: Starting Pyrogram...")
        loop.run_until_complete(pyrogram_client.start())
        
        # Check if we are actually logged in
        me = loop.run_until_complete(pyrogram_client.get_me())
        logger.info(f"✅ Background thread: Connected as {me.first_name} (ID: {me.id})")
        
        # Signal that we are ready
        startup_event.set()
        
        # Keep the loop running
        loop.run_forever()
        
    except Exception as e:
        logger.critical(f"Background thread: Failed to start - {e}")
        startup_event.set() # Release lock even on failure

# Start the background thread immediately when the module loads
# This ensures it's ready before Gunicorn starts accepting requests
t = threading.Thread(target=run_pyrogram_background, daemon=True)
t.start()

# ─── HELPER FUNCTIONS ───

async def get_card_response(cc_number):
    """
    Sends command to bot, waits 5s, fetches and parses response.
    """
    try:
        if not pyrogram_client.is_connected:
            raise Exception("Pyrogram client is disconnected")
            
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
            
    except KeyError as e:
        # Handle "Username not found" specifically
        logger.error(f"Username Resolution Error: {e}")
        return "Error: Bot username not found or account restricted."
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
        
        # Clean input: Remove leading '=' if present
        if cc_details.startswith("="):
            cc_details = cc_details[1:]
            
        logger.info(f"--- New Request ---")
        logger.info(f"Card Details: {cc_details}")
        
        # Wait for the background thread to be ready (just in case)
        if not startup_event.is_set():
            logger.warning("Pyrogram not ready yet. Waiting 2s...")
            startup_event.wait(timeout=2)
            
        if loop is None or pyrogram_client is None:
             return jsonify({"error": "Service Unavailable: Userbot not initialized"}), 503

        # Run the async function in the background loop
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
            
        # Logic: "Username not found"
        elif "Username not found" in raw_response:
            status = "ERROR"
            final_response_text = "Restricted Account / Bot Not Found"

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
