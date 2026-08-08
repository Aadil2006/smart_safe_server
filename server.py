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
# 3. ULTIMATE WEB DASHBOARD (UI 3.0)
# ==========================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Safe Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --accent: #3b82f6; --text: #f8fafc; --border: #334155; --success: #10b981; --danger: #ef4444; --warning: #f59e0b; --th-bg: #0b1120; }
        body.light-mode { --bg: #f1f5f9; --card: #ffffff; --accent: #2563eb; --text: #0f172a; --border: #cbd5e1; --th-bg: #e2e8f0; }
        
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; transition: 0.3s; }
        .container { max-width: 1000px; margin: auto; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }
        h1 { color: var(--accent); margin: 0; font-size: 26px; display: flex; align-items: center; gap: 10px; }
        
        /* 🔴 Blinking Live Dot */
        .live-dot { width: 12px; height: 12px; background-color: var(--danger); border-radius: 50%; box-shadow: 0 0 10px var(--danger); animation: blink 1.5s infinite; }
        @keyframes blink { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } 100% { opacity: 1; transform: scale(1); } }
        
        .controls { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .btn { padding: 10px 18px; background: var(--card); border: 2px solid var(--accent); color: var(--text); border-radius: 8px; cursor: pointer; transition: 0.3s; font-weight: bold; }
        .btn:hover { background: var(--accent); color: #fff; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(59, 130, 246, 0.3); }
        .btn-danger { border-color: var(--danger); color: var(--danger); }
        .btn-danger:hover { background: var(--danger); color: white; box-shadow: 0 5px 15px rgba(239, 68, 68, 0.3); }
        .search-box { padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--card); color: var(--text); flex-grow: 1; font-size: 16px; outline: none; transition: 0.3s; }
        .search-box:focus { border-color: var(--accent); box-shadow: 0 0 10px rgba(59, 130, 246, 0.2); }
        
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }
        .stat-card { background: var(--card); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .stat-card h3 { margin: 0; font-size: 14px; color: #94a3b8; text-transform: uppercase; }
        .stat-card h2 { margin: 10px 0 0 0; font-size: 32px; }
        
        table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 10px; overflow: hidden; border: 1px solid var(--border); }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid var(--border); }
        th { background: var(--th-bg); color: var(--accent); text-transform: uppercase; font-size: 0.9em; }
        tr:hover { background: rgba(59, 130, 246, 0.05); }
        
        .badge { padding: 6px 12px; border-radius: 20px; font-size: 0.85em; font-weight: bold; display: inline-block; }
        .badge.granted { background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid var(--success); }
        .badge.denied { background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid var(--danger); }
        .badge.locked { background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid var(--warning); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><div class="live-dot"></div> 🛡️ Command Center</h1>
            <div>
                <button id="themeBtn" class="btn" onclick="toggleTheme()" style="margin-right: 10px;">☀️ Light Mode</button>
                <span style="color: #94a3b8; font-size: 14px;">Logged in as <b>Admin</b></span>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><h3>Total Activity</h3><h2 id="totalLogs">0</h2></div>
            <div class="stat-card"><h3>Successful Unlocks</h3><h2 id="totalGranted" style="color: var(--success);">0</h2></div>
            <div class="stat-card"><h3>Breach Attempts</h3><h2 id="totalDenied" style="color: var(--danger);">0</h2></div>
        </div>
        
        <div class="controls">
            <button class="btn btn-danger" onclick="remoteUnlock()">🔓 Remote Unlock</button>
            <button class="btn" onclick="exportCSV()">📥 Download CSV Logs</button>
            <input type="text" id="searchInput" class="search-box" placeholder="🔍 Search logs by User, Date, or Status..." onkeyup="filterTable()">
        </div>

        <table id="logTable">
            <tr><th>Date & Time</th><th>User Identity</th><th>Status</th></tr>
            {% for log in logs %}
            <tr>
                <td>{{ log.time_str }}</td>
                <td>
                    <!-- 🧑‍💻 Smart Avatars Logic -->
                    {% if 'Aadil' in log.rfid_tag %}
                        <span style="font-size: 1.2em;">🧑‍💻</span>
                    {% elif 'Family' in log.rfid_tag %}
                        <span style="font-size: 1.2em;">👨‍👩‍👦</span>
                    {% elif 'PIN' in log.rfid_tag %}
                        <span style="font-size: 1.2em;">🔢</span>
                    {% elif 'App' in log.rfid_tag %}
                        <span style="font-size: 1.2em;">📱</span>
                    {% else %}
                        <span style="font-size: 1.2em;">⚠️</span>
                    {% endif %}
                    <strong>{{ log.rfid_tag }}</strong>
                </td>
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
            <tr><td colspan="3" id="noRecords" style="text-align: center; color: #94a3b8;">Scanning for live events...</td></tr>
            {% endfor %}
        </table>
    </div>

    <script>
        // 1. Theme Logic
        function toggleTheme() {
            document.body.classList.toggle('light-mode');
            let btn = document.getElementById('themeBtn');
            if(document.body.classList.contains('light-mode')) {
                btn.innerText = '🌙 Dark Mode'; localStorage.setItem('theme', 'light');
            } else {
                btn.innerText = '☀️ Light Mode'; localStorage.setItem('theme', 'dark');
            }
        }
        if(localStorage.getItem('theme') === 'light') toggleTheme();

        // 2. Dynamic Stats
        function updateStats() {
            let rows = document.querySelectorAll("#logTable tr");
            let total = 0, granted = 0, denied = 0;
            if(document.getElementById("noRecords")) return; 
            for (let i = 1; i < rows.length; i++) {
                if (rows[i].style.display !== "none") {
                    total++;
                    let statusText = rows[i].cells[2].innerText.toUpperCase();
                    if(statusText.includes("GRANTED") || statusText.includes("UNLOCKED")) granted++;
                    if(statusText.includes("DENIED") || statusText.includes("LOCKOUT")) denied++;
                }
            }
            document.getElementById("totalLogs").innerText = total;
            document.getElementById("totalGranted").innerText = granted;
            document.getElementById("totalDenied").innerText = denied;
        }
        window.onload = updateStats;

        // 3. Live Search Filter
        function filterTable() {
            let filter = document.getElementById("searchInput").value.toUpperCase();
            let tr = document.getElementById("logTable").getElementsByTagName("tr");
            for (let i = 1; i < tr.length; i++) {
                let txtValue = tr[i].textContent || tr[i].innerText;
                tr[i].style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? "" : "none";
            }
            updateStats(); 
        }

        // 4. Remote Unlock + 🗣️ A.I. VOICE ANNOUNCER
        function remoteUnlock() {
            if(confirm("⚠️ SECURITY WARNING: Unlock the safe remotely?")) {
                
                // Voice Announcement Logic
                let speech = new SpeechSynthesisUtterance();
                speech.text = "Warning. Initiating remote unlock sequence for the smart safe.";
                speech.volume = 1; speech.rate = 0.9; speech.pitch = 1;
                window.speechSynthesis.speak(speech);

                fetch('/web_unlock', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    setTimeout(() => {
                        let successSpeech = new SpeechSynthesisUtterance("Unlock command sent successfully.");
                        window.speechSynthesis.speak(successSpeech);
                        alert("✅ Unlock Command Sent!");
                        location.reload();
                    }, 2500); // Waits for the first voice to finish
                });
            }
        }

        // 5. CSV Export
        function exportCSV() {
            let rows = document.querySelectorAll("#logTable tr");
            let csv = [];
            for (let i = 0; i < rows.length; i++) {
                if(rows[i].style.display !== "none") {
                    let row = [], cols = rows[i].querySelectorAll("td, th");
                    for (let j = 0; j < cols.length; j++) row.push('"' + cols[j].innerText.replace(/[^a-zA-Z0-9 :/-]/g, "").trim() + '"');
                    csv.push(row.join(","));
                }
            }
            let link = document.createElement("a");
            link.download = "SmartSafe_Access_Logs.csv";
            link.href = window.URL.createObjectURL(new Blob([csv.join("\\n")], {type: "text/csv"}));
            link.click();
        }

        setInterval(() => { if(!document.getElementById("searchInput").value) location.reload(); }, 30000);
    </script>
</body>
</html>
"""
# ==========================================
# 📧 EMAIL SENDING API (GOOGLE APPS SCRIPT)
# ==========================================
# 👇 YAHAN APNA GOOGLE SCRIPT WALA LINK WAPAS PASTE KAR DENA 👇
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzyrcRKzeJ_RbCNPiPpu9EM_uMgsjue1kUhru1UnezR_NLw0isrWO6ngMwt7nR5h5lR/exec"
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
    # Changed limit to 100 to show more data in analytics
    logs_cursor = collection.find().sort("timestamp", -1).limit(100)
    logs_list = [{"time_str": log['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(log.get('timestamp'), datetime) else "Unknown", "rfid_tag": log.get('rfid_tag', ''), "status": log.get('status', '')} for log in logs_cursor]
    return render_template_string(DASHBOARD_HTML, logs=logs_list)

@app.route('/web_unlock', methods=['POST'])
def web_unlock():
    requests.get(f"{BLYNK_URL}/update?token={BLYNK_AUTH_TOKEN}&v4=1")
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
