import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# === environment variables ===
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

@app.route("/")
def home():
    return "Novacool AI backend is running"

@app.route("/ask", methods=["POST"])
def ask():
    try:
        question = request.json.get("question", "").strip()
        if not question:
            return jsonify({"error": "No question received"}), 400

        if not OPENAI_KEY:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500

        if not PROJECT_ID:
            return jsonify({"error": "Missing OPENAI_PROJECT_ID"}), 500

        url = f"https://api.openai.com/v1/projects/{PROJECT_ID}/responses"

        payload = {
            "model": "gpt-4o-mini",      # fast + inexpensive
            "input": question
        }

        headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }

        r = requests.post(url, json=payload, headers=headers, timeout=60)
        data = r.json()

        print("\n[OPENAI RESPONSE RAW]\n", data, "\n")  # Visible in Render logs for debugging

        # === success ===
        if "output_text" in data:
            return jsonify({"answer": data["output_text"]})

        # === OpenAI error bubble ===
        if "error" in data:
            return jsonify({"error": data["error"]["message"]}), 500

        return jsonify({"error": "Unexpected response format"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
