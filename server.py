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

# ==========================================
# 3. ADVANCED WEB DASHBOARD (UI 2.0)
# ==========================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Safe Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --accent: #3b82f6; --text: #f8fafc; --success: #10b981; --danger: #ef4444; --warning: #f59e0b; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; flex-wrap: wrap; gap: 10px; }
        h1 { color: var(--accent); margin: 0; font-size: 24px; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        
        .btn { padding: 12px 20px; background: var(--card); border: 2px solid var(--accent); color: var(--text); border-radius: 8px; cursor: pointer; transition: 0.3s; font-weight: bold; }
        .btn:hover { background: var(--accent); }
        .btn-danger { border-color: var(--danger); color: var(--danger); }
        .btn-danger:hover { background: var(--danger); color: white; }
        
        .search-box { padding: 12px; border-radius: 8px; border: 1px solid #334155; background: var(--card); color: white; flex-grow: 1; font-size: 16px; outline: none; }
        .search-box:focus { border-color: var(--accent); }
        
        table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #334155; }
        th { background: #0b1120; color: var(--accent); text-transform: uppercase; font-size: 0.9em; letter-spacing: 1px; }
        tr:hover { background: #334155; }
        
        /* Badges for Status */
        .badge { padding: 6px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; display: inline-block; }
        .badge.granted { background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); }
        .badge.denied { background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
        .badge.locked { background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Smart Safe Command Center</h1>
            <span style="color: #94a3b8; font-size: 14px;">Logged in as <b>Admin</b></span>
        </div>
        
        <div class="controls">
            <button class="btn btn-danger" onclick="remoteUnlock()">🔓 Remote Unlock</button>
            <button class="btn" onclick="exportCSV()">📥 Download CSV Logs</button>
            <input type="text" id="searchInput" class="search-box" placeholder="🔍 Search logs by User, Date, or Status..." onkeyup="filterTable()">
        </div>

        <table id="logTable">
            <tr><th>Date & Time</th><th>User / Method</th><th>Status</th></tr>
            {% for log in logs %}
            <tr>
                <td>{{ log.time_str }}</td>
                <td><strong>{{ log.rfid_tag }}</strong></td>
                <td>
                    {% if 'Granted' in log.status or 'Unlocked' in log.status %}
                        <span class="badge granted">{{ log.status }}</span>
                    {% elif 'Denied' in log.status or 'Lockout' in log.status %}
                        <span class="badge denied">{{ log.status }}</span>
                    {% else %}
                        <span class="badge locked">{{ log.status }}</span>
                    {% endif %}
                </td>
            </tr>
            {% else %}
            <tr><td colspan="3" style="text-align: center; color: #94a3b8;">No records yet. Waiting for Safe to connect...</td></tr>
            {% endfor %}
        </table>
    </div>

    <script>
        // 1. Remote Unlock Function
        function remoteUnlock() {
            if(confirm("⚠️ SECURITY WARNING: Are you sure you want to unlock the safe remotely?")) {
                fetch('/web_unlock', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert("✅ Unlock Command Sent to Safe!");
                    setTimeout(() => location.reload(), 2000);
                });
            }
        }

        // 2. Live Search Filter
        function filterTable() {
            let input = document.getElementById("searchInput");
            let filter = input.value.toUpperCase();
            let table = document.getElementById("logTable");
            let tr = table.getElementsByTagName("tr");
            
            for (let i = 1; i < tr.length; i++) {
                let txtValue = tr[i].textContent || tr[i].innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    tr[i].style.display = "";
                } else {
                    tr[i].style.display = "none";
                }
            }
        }

        // 3. Export to CSV Excel
        function exportCSV() {
            let table = document.getElementById("logTable");
            let rows = table.querySelectorAll("tr");
            let csv = [];
            for (let i = 0; i < rows.length; i++) {
                let row = [], cols = rows[i].querySelectorAll("td, th");
                for (let j = 0; j < cols.length; j++) row.push('"' + cols[j].innerText + '"');
                csv.push(row.join(","));
            }
            let csvFile = new Blob([csv.join("\\n")], {type: "text/csv"});
            let downloadLink = document.createElement("a");
            downloadLink.download = "SmartSafe_Access_Logs.csv";
            downloadLink.href = window.URL.createObjectURL(csvFile);
            downloadLink.style.display = "none";
            document.body.appendChild(downloadLink);
            downloadLink.click();
        }

        // 4. Auto-refresh page every 30 seconds (Only if not typing in search)
        setInterval(() => {
            if(!document.getElementById("searchInput").value) {
                location.reload();
            }
        }, 30000);
    </script>
</body>
</html>
"""

# ==========================================
# 📧 EMAIL SENDING API (GOOGLE APPS SCRIPT)
# ==========================================
# 👇 YAHAN APNA GOOGLE SCRIPT WALA LINK WAPAS PASTE KAR DENA 👇
GOOGLE_SCRIPT_URL = "TERA_GOOGLE_SCRIPT_LINK_YAHAN_DAAL"
EMAIL_ID = "aadilarora36@gmail.com"

def send_email_sync(subject, body):
    try:
        payload = {"subject": subject, "body": body, "email": EMAIL_ID}
        headers = {"Content-Type": "application/json"}
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200: return True, "Email sent successfully!"
        else: return False, f"HTTP Error: {response.text}"
    except Exception as e: return False, str(e)

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
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/test_email', methods=['GET'])
def test_email():
    success, msg = send_email_sync("🛠️ Smart Safe Setup", "Bhai Aadil! Tera naya Google API wala system ekdum makkhan chal raha hai.")
    if success: return f"<h1>✅ EMAIL COMMAND SENT!</h1><p>Check {EMAIL_ID} Inbox.</p>"
    else: return f"<h1>❌ FAILED!</h1><pre style='color:red;'>{msg}</pre>"

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

        try: requests.get(f"{BLYNK_URL}/update?token={BLYNK_AUTH_TOKEN}&v2={alert_msg}")
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
