from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# =========================
# Home (basic health check)
# =========================
@app.route("/")
def home():
    return "Novacool AI is running"

# =========================
# Full Chat UI  (front-end)
# =========================
@app.route("/chat")
def chat():
    return render_template("chat.html")

# =========================
# Ask endpoint (backend)
# =========================
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        question = data.get("question", "")
        if not question:
            return jsonify({"error": "No question received"}), 400

        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500

        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are the Novacool AI assistant. Answer accurately using product data."},
                    {"role": "user", "content": question}
                ]
            }
        )

        result = r.json()
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================
# File uploader page (from ZIP backup)
# — this stays, unchanged
# =========================
@app.route("/upload")
def upload():
    return render_template("uploader.html")

# =========================
# Start app
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
