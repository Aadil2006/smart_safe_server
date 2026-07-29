import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Tera MongoDB Database URL
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

@app.route('/log', methods=['POST'])
def log_access():
    try:
        data = request.get_json()
        log_entry = {
            "rfid_tag": data.get("rfid_tag", "Unknown"),
            "status": data.get("status", "Unknown"),
            "timestamp": datetime.now()
        }
        collection.insert_one(log_entry)
        print(f"📝 Log Saved: {log_entry['status']} | Tag: {log_entry['rfid_tag']}")
        return jsonify({"message": "Log saved"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_pin', methods=['GET'])
def get_pin():
    try:
        doc = settings_collection.find_one({"type": "master_pin"})
        print(f"☁️ ESP32 Requested PIN. Sending: {doc['pin']}")
        return jsonify({"pin": str(doc["pin"])}), 200
    except Exception as e:
        print("❌ Error fetching PIN:", e)
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
        print("❌ Error updating PIN:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Cloud deployment ke liye dynamic port assign kiya hai
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)