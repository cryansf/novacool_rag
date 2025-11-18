import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# =========================
# 🔐 Environment Settings
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================
# 🚦 Basic Health Check
# =========================
@app.route("/")
def index():
    return "Novacool AI backend is running", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


# =========================
# 🌐 Full-Page Chat UI
# =========================
@app.route("/chat")
def chat_page():
    return render_template("chat.html")


# =========================
# 🧠 Ask Novacool AI
# =========================
@app.route("/ask", methods=["POST"])
def ask():
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500

        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

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
                        "You are Novacool AI, an assistant for SW Firefighting Foam. "
                        "Base your responses ONLY on known Novacool UEF information. "
                        "If unsure, say so — do not guess."
                    )
                },
                {"role": "user", "content": question}
            ],
            "temperature": 0.4
        }

        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if not r.ok:
            try:
                err = r.json()
                msg = err.get("error", {}).get("message")
                return jsonify({"error": msg}), 500
            except:
                return jsonify({"error": r.text}), 500

        answer = (
            r.json()
             .get("choices", [{}])[0]
             .get("message", {})
             .get("content", "")
             .strip()
        )

        return jsonify({"answer": answer}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 📚 Upload Files (PDF/DOCX)
# =========================
@app.route("/upload", methods=["GET"])
def upload_page():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "No files"}), 400

    files = request.files.getlist('files')
    saved = []

    for file in files:
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        saved.append(filename)

    return jsonify({"uploaded": saved}), 200


@app.route("/reindex", methods=["POST"])
def reindex():
    # Placeholder for restoring FAISS ingestion
    return jsonify({"status": "Reindex triggered (stub)"}), 200


# =========================
# 🔥 Local Dev Only
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
