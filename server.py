import os
from flask import Flask, request, jsonify, render_template_string, Response
from pymongo import MongoClient
from datetime import datetime
import threading
import requests

app = Flask(__name__)

# ==========================================
# 1. BLYNK & DASHBOARD SETTINGS
# ==========================================
BLYNK_AUTH_TOKEN = "l3i7rUSmcoZ8n9-ZTZ9xeRNn1Pa-pgVQ"
BLYNK_URL = "https://blr1.blynk.cloud/external/api" 
WEB_USER = "admin"
WEB_PASS = "12345"

# ==========================================
# 2. MONGODB DATABASE SETUP
# ==========================================
MONGO_URI = "mongodb+srv://aadilarora36_db_user:Aadil12345@cluster0.4i4g8sr.mongodb.net/?appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["SmartSafeDB"]
    collection = db["logs"]
    settings_collection = db["settings"]
    
    if settings_collection.count_documents({"type": "master_pin"}) == 0:
        settings_collection.insert_one({"type": "master_pin", "pin": "1234"})

    print("✅ Server Started & Database Connected Successfully.")
except Exception as e:
    print("❌ Database Connection Error:", e)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Safe Web Portal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a2e; color: white; text-align: center; margin: 0; padding: 20px;}
        h1 { color: #e94560; }
        table { width: 100%; max-width: 800px; margin: 20px auto; border-collapse: collapse; background: #16213e; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        th, td { padding: 15px; border-bottom: 1px solid #0f3460; }
        th { background: #e94560; color: white; text-transform: uppercase; }
        tr:hover { background-color: #0f3460; }
        .btn { padding: 15px 40px; background: #0f3460; color: white; border: 2px solid #e94560; font-size: 20px; font-weight: bold; cursor: pointer; border-radius: 8px; transition: 0.3s; margin-bottom: 20px; }
        .btn:hover { background: #e94560; }
    </style>
</head>
<body>
    <h1>🔐 Smart Safe Web Portal</h1>
    <p>Logged in as Administrator</p>
    <button class="btn" onclick="remoteUnlock()">🔓 UNLOCK SAFE (REMOTE)</button>
    <h2>Live Access Records (From MongoDB)</h2>
    <table>
        <tr><th>Date & Time</th><th>User / Method</th><th>Status</th></tr>
        {% for log in logs %}
        <tr><td>{{ log.time_str }}</td><td>{{ log.rfid_tag }}</td><td>{{ log.status }}</td></tr>
        {% else %}
        <tr><td colspan="3">No records yet. Waiting for Safe to connect...</td></tr>
        {% endfor %}
    </table>
    <script>
        function remoteUnlock() {
            fetch('/web_unlock', { method: 'POST' })
            .then(response => response.json())
            .then(data => alert("Unlock Command Sent to Safe!"));
        }
    </script>
</body>
</html>
"""

# ==========================================
# 📧 EMAIL SENDING API (GOOGLE APPS SCRIPT) - 100% BULLETPROOF
# ==========================================
# 👇 YAHAN APNA GOOGLE SCRIPT WALA LINK PASTE KAR 👇
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzyrcRKzeJ_RbCNPiPpu9EM_uMgsjue1kUhru1UnezR_NLw0isrWO6ngMwt7nR5h5lR/exec"
EMAIL_ID = "aadilarora36@gmail.com"

def send_email_sync(subject, body):
    try:
        payload = {
            "subject": subject,
            "body": body,
            "email": EMAIL_ID
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return True, "Email sent via Google API successfully!"
        else:
            return False, f"HTTP Error: {response.text}"
    except Exception as e:
        return False, str(e)

def send_email_async(subject, body):
    send_email_sync(subject, body)

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        data = request.get_json()
        subject = data.get("subject", "Smart Safe Alert")
        body = data.get("body", "")
        threading.Thread(target=send_email_async, args=(subject, body)).start()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test_email', methods=['GET'])
def test_email():
    if GOOGLE_SCRIPT_URL == "TERA_GOOGLE_SCRIPT_LINK_YAHAN_DAAL":
        return "<h1>❌ FAILED!</h1><p>Bhai pehle server.py me apna Google Script ka link toh paste kar line 76 par!</p>"
    
    success, msg = send_email_sync("🛠️ Smart Safe Setup", "Bhai Aadil! Tera naya Google API wala system ekdum makkhan chal raha hai. Ab Render ya Cloudflare tujhe block nahi kar sakte!")
    if success:
        return f"<h1>✅ EMAIL COMMAND SENT!</h1><p>Apna {EMAIL_ID} ka Inbox check kar. Email instantly aa gayi hogi bina kisi error ke!</p>"
    else:
        return f"<h1>❌ FAILED!</h1><p>Error message yeh hai:</p><pre style='color:red;'>{msg}</pre>"

# ==========================================
# 4. API FOR ESP32 & BLYNK
# ==========================================

@app.route('/log', methods=['POST'])
def log_access():
    try:
        data = request.get_json()
        tag = data.get("rfid_tag", "Unknown")
        status = data.get("status", "Unknown")
        log_entry = {"rfid_tag": tag, "status": status, "timestamp": datetime.now()}
        collection.insert_one(log_entry)
        
        alert_msg = ""
        if status == "Lockout": alert_msg = "🚨 SECURITY: 30s Lockout Active!"
        elif status == "Locked": alert_msg = "🔒 Safe is now Locked"
        elif "Denied" in status: alert_msg = f"🚫 Intruder: {tag} Denied!"
        else: alert_msg = f"✅ Unlocked by {tag}"

        try:
            requests.get(f"{BLYNK_URL}/update?token={BLYNK_AUTH_TOKEN}&v2={alert_msg}")
        except: pass
        return jsonify({"message": "Log saved"}), 201
    except Exception as e: return jsonify({"error": str(e)}), 500

def clear_otp():
    try: requests.get(f"{BLYNK_URL}/update?token={BLYNK_AUTH_TOKEN}&v1=---")
    except: pass

@app.route('/send_otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        otp = data.get('otp', '0000')
        requests.get(f"{BLYNK_URL}/update?token={BLYNK_AUTH_TOKEN}&v1=OTP: {otp}")
        threading.Timer(60.0, clear_otp).start()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/blynk_sync', methods=['GET', 'POST'])
def blynk_sync():
    try:
        if request.method == 'POST':
            state = request.get_json().get("state", "0")
            requests.get(f"{BLYNK_URL}/update?token={BLYNK_AUTH_TOKEN}&v4={state}", timeout=5)
            return jsonify({"success": True})
        else:
            res = requests.get(f"{BLYNK_URL}/get?token={BLYNK_AUTH_TOKEN}&v4", timeout=5)
            if res.status_code == 200 and "1" in res.text: return "1"
            elif res.status_code == 200 and "0" in res.text: return "0"
            else: return "ERROR"
    except: return "ERROR"

@app.route('/get_pin', methods=['GET'])
def get_pin():
    try:
        doc = settings_collection.find_one({"type": "master_pin"})
        return jsonify({"pin": str(doc["pin"])}), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/update_pin', methods=['POST'])
def update_pin():
    try:
        new_pin = request.get_json().get("new_pin")
        settings_collection.update_one({"type": "master_pin"}, {"$set": {"pin": str(new_pin)}})
        return jsonify({"message": "PIN updated"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    auth = request.authorization
    if not auth or not (auth.username == WEB_USER and auth.password == WEB_PASS):
        return Response('Security Alert: Login Required.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
    logs_cursor = collection.find().sort("timestamp", -1).limit(50)
    logs_list = [{"time_str": log['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(log.get('timestamp'), datetime) else "Unknown", "rfid_tag": log.get('rfid_tag', ''), "status": log.get('status', '')} for log in logs_cursor]
    return render_template_string(DASHBOARD_HTML, logs=logs_list)

@app.route('/web_unlock', methods=['POST'])
def web_unlock():
    requests.get(f"{BLYNK_URL}/update?token={BLYNK_AUTH_TOKEN}&v4=1")
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
