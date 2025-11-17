import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")         # your sk-proj key
PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")      # must be added in Render dashboard

@app.route("/")
def home():
    return "Novacool AI backend running"

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/uploader")
def uploader_page():
    return render_template("uploader.html")

@app.route("/ask", methods=["POST"])
def ask():
    try:
        body = request.get_json()
        question = body.get("question", "").strip()

        if not question:
            return jsonify({"error": "No question received"}), 400
        if not OPENAI_KEY:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500
        if not PROJECT_ID:
            return jsonify({"error": "Missing OPENAI_PROJECT_ID"}), 500

        # NEW endpoint required for sk-proj keys
        response = requests.post(
            f"https://api.openai.com/v1/projects/{PROJECT_ID}/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-5.1-mini",
                "input": question,
            },
            timeout=60
        )

        data = response.json()

        # debug capture if needed
        # print(data)

        if "output_text" in data:
            answer = data["output_text"]
            return jsonify({"answer": answer})

        elif "error" in data:
            return jsonify({"error": data["error"]["message"]}), 500

        else:
            return jsonify({"error": "Unknown response format"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
