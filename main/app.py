from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect
from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Crucial for security sessions to work
app.secret_key = 'mindshield_super_secret_key_2026'

# Configure New Gemini API
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("⚠️ WARNING: GEMINI_API_KEY environment variable not set.")

# ==========================================
# 📊 ANALYTICS ENGINE (ANONYMIZED)
# ==========================================
ANALYTICS_FILE = 'analytics.json'

def load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE, 'r') as f:
            return json.load(f)
    # Default blank state
    return {"total_assessments": 0, "high_risk_alerts": 0, "anxiety_scores": [], "burnout_scores": []}

def save_analytics(data):
    with open(ANALYTICS_FILE, 'w') as f:
        json.dump(data, f)

def update_metrics_from_assessment(ai_response_text):
    """Extracts scores from the AI's JSON output to feed the admin dashboard"""
    try:
        # Find the JSON part of the string
        json_str = ai_response_text.split('ASSESSMENT_COMPLETE')[1].strip()
        data = json.loads(json_str)
        
        metrics = load_analytics()
        metrics["total_assessments"] += 1
        
        if data.get("risk_level") == "high":
            metrics["high_risk_alerts"] += 1
            
        metrics["anxiety_scores"].append(data.get("anxiety_score", 5))
        metrics["burnout_scores"].append(data.get("burnout_score", 5))
        
        save_analytics(metrics)
    except Exception as e:
        print(f"Failed to parse metrics: {e}")

# ==========================================
# 🌐 ROUTES
# ==========================================

@app.route('/')
def home():
    return render_template('MindShieldAI_Premium.html')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/json')

# ==========================================
# 🔒 SECURE ADMIN PANEL
# ==========================================

@app.route('/admin')
def admin_dashboard():
    # Check if the user is logged into the session
    if not session.get('admin_logged_in'):
        return render_template('admin.html', logged_in=False)
    
    return render_template('admin.html', logged_in=True)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    # Get the password the user typed in
    password_attempt = request.form.get('password')
    
    # Securely grab the real password from your .env vault
    secure_password = os.environ.get("ADMIN_PASSWORD")
    
    # Check if they match
    if password_attempt == secure_password:
        session['admin_logged_in'] = True
        
    return redirect('/admin')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin')

@app.route('/api/analytics')
def get_analytics():
    """API endpoint for the dashboard to fetch live data"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(load_analytics())

# ==========================================
# 🤖 GEMINI LLM CHAT API
# ==========================================

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    system_prompt = data.get('system', '')
    frontend_messages = data.get('messages', [])

    try:
        # Convert frontend history to new google.genai format
        gemini_history = []
        for msg in frontend_messages[:-1]: # Everything except the latest message
            role = "model" if msg.get("role") == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        current_message = frontend_messages[-1].get("content", "Hello") if frontend_messages else "Hello"

        # Using the new google.genai SDK method
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config={"system_instruction": system_prompt},
            history=gemini_history
        )
        
        response = chat.send_message(current_message)
        reply_text = response.text
        
        # If assessment finished, quietly update our live analytics!
        if "ASSESSMENT_COMPLETE" in reply_text:
            update_metrics_from_assessment(reply_text)

        return jsonify({"reply": reply_text})

    except Exception as e:
        print(f"Gemini API Error: {e}")
        # 🔥 The Fallback Feature: Instead of crashing, send a clean chat bubble back to the user!
        fallback_msg = (
            "Hey! My daily AI limit is maxed out from too many visitors today. 😅 "
            "Please try again after some time! till then you can play games from games tab!!"
        )
        return jsonify({"reply": fallback_msg})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)