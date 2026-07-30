import os
from flask import Flask, request, jsonify, render_template_string, Response
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)

# ==========================================
# 1. BLYNK & DASHBOARD SETTINGS
# ==========================================
BLYNK_AUTH_TOKEN = "l3i7rUSmcoZ8n9-ZTZ9xeRNn1Pa-pgVQ" # <-- Apna Blynk token yahan daal
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
    
    # Agar database me PIN nahi hai, toh default '1234' set kar dega
    if settings_collection.count_documents({"type": "master_pin"}) == 0:
        settings_collection.insert_one({"type": "master_pin", "pin": "1234"})

    client.server_info() 
    print("✅ Server Started & Database Connected Successfully.")
except Exception as e:
    print("❌ Database Connection Error:", e)

# Remote unlock check karne ke liye variable
unlock_flag = False

# ==========================================
# 3. HTML WEB DASHBOARD (UI Design)
# ==========================================
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
# 4. API FOR ESP32 & BLYNK
# ==========================================

@app.route('/log', methods=['POST'])
def log_access():
    try:
        data = request.get_json()
        tag = data.get("rfid_tag", "Unknown")
        status = data.get("status", "Unknown")
        
        # 1. MongoDB me log save karna
        log_entry = {
            "rfid_tag": tag,
            "status": status,
            "timestamp": datetime.now()
        }
        collection.insert_one(log_entry)
        print(f"📝 MongoDB Log Saved: {status} | Tag: {tag}")
        
        # 2. Blynk V2 par Live Alert bhejna
        try:
            if "Denied" in status or "Incorrect" in status or "LOCKED" in status:
                requests.get(f"https://blynk.cloud/external/api/update?token={BLYNK_AUTH_TOKEN}&V2=🚨 Alert: {tag} ({status})")
            else:
                requests.get(f"https://blynk.cloud/external/api/update?token={BLYNK_AUTH_TOKEN}&V2=✅ {tag} ({status})")
        except Exception as e:
            print("Blynk Alert Error:", e)

        return jsonify({"message": "Log saved"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/send_otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        otp = data.get('otp', '0000')
        # Blynk V1 par OTP bhejna
        requests.get(f"https://blynk.cloud/external/api/update?token={BLYNK_AUTH_TOKEN}&V1={otp}")
        print(f"📲 OTP {otp} sent to Blynk V1")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/check_unlock', methods=['GET'])
def check_unlock():
    global unlock_flag
    should_unlock = unlock_flag
    
    # Agar Web Dashboard se unlock daba hai
    if unlock_flag:
        unlock_flag = False 
        
    # Agar Blynk App (V3) se unlock daba hai
    try:
        res = requests.get(f"https://blynk.cloud/external/api/get?token={BLYNK_AUTH_TOKEN}&V3")
        if res.status_code == 200 and int(res.json()[0]) == 1:
            should_unlock = True
            # Button ko wapas 0 (Off) kar do
            requests.get(f"https://blynk.cloud/external/api/update?token={BLYNK_AUTH_TOKEN}&V3=0")
    except:
        pass

    return jsonify({"unlock": should_unlock})

@app.route('/get_pin', methods=['GET'])
def get_pin():
    try:
        doc = settings_collection.find_one({"type": "master_pin"})
        print(f"☁️ ESP32 Requested PIN. Sending: {doc['pin']}")
        return jsonify({"pin": str(doc["pin"])}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update_pin', methods=['POST'])
def update_pin():
    try:
        data = request.get_json()
        new_pin = data.get("new_pin")
        settings_collection.update_one({"type": "master_pin"}, {"$set": {"pin": str(new_pin)}})
        print(f"🔄 Password Updated by ESP32 to: {new_pin}")
        return jsonify({"message": "PIN updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 5. WEB ROUTES (Login & UI)
# ==========================================
@app.route('/')
def index():
    auth = request.authorization
    # Native Browser Login Verification
    if not auth or not (auth.username == WEB_USER and auth.password == WEB_PASS):
        return Response('Security Alert: Login Required to access Smart Safe.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
    
    # MongoDB se last 50 logs nikal kar Dashboard par bhejna
    logs_cursor = collection.find().sort("timestamp", -1).limit(50)
    logs_list = []
    for log in logs_cursor:
        time_format = log['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(log.get('timestamp'), datetime) else "Unknown Time"
        logs_list.append({"time_str": time_format, "rfid_tag": log.get('rfid_tag', ''), "status": log.get('status', '')})
        
    return render_template_string(DASHBOARD_HTML, logs=logs_list)

@app.route('/web_unlock', methods=['POST'])
def web_unlock():
    global unlock_flag
    unlock_flag = True
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
