import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # your sk- or sk-proj key
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@app.route("/")
def index():
    return "Novacool AI backend is running", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/chat")
def chat_page():
    # Full-page chat UI
    return render_template("chat.html")


@app.route("/ask", methods=["POST"])
def ask():
    """
    Frontend calls this with JSON:
      { "question": "..." }
    We call OpenAI and return:
      { "answer": "..." }  OR  { "error": "..." }
    """
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "Missing OPENAI_API_KEY in environment"}), 500

        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        # --- Call OpenAI Chat Completions API ---
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Novacool AI, an assistant for SW Firefighting Foam & Equipment. "
                        "Answer clearly and concisely based on what you know about Novacool UEF, "
                        "its mix ratios, applications, certifications, environmental profile, "
                        "and firefighting best practices. If you don't know, say so."
                    ),
                },
                {"role": "user", "content": question},
            ],
            "temperature": 0.4,
        }

        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if not r.ok:
            # Try to surface OpenAI error message
            try:
                err = r.json()
                msg = err.get("error", {}).get("message", r.text)
            except Exception:
                msg = r.text
            return jsonify({"error": f"OpenAI error: {msg}"}), 500

        resp = r.json()
        answer = (
            resp.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            return jsonify({"error": "Empty answer from OpenAI"}), 500

        return jsonify({"answer": answer}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Local dev only; Render will use gunicorn
    app.run(host="0.0.0.0", port=5000)
