import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rag_pipeline import embed_and_store, search_vector_store

app = Flask(__name__)
CORS(app)  # Allow frontend requests

CHAT_MODEL = "gpt-4o-mini"

# ========== HEALTH CHECK ==========
@app.route("/health")
def health():
    return "OK", 200


# ========== CHAT ENDPOINT ==========
@app.route("/chat", methods=["POST"])
def chat():
    try:
        question = request.json.get("question", "").strip()
        if not question:
            return jsonify({"error": "No question provided"}), 400

        top_chunks = search_vector_store(question)
        context = "\n\n".join(c["text"] for c in top_chunks)
        sources = list({c["file"] for c in top_chunks})

        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500

        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": "You are Novacool’s assistant. Cite filenames."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
                ]
            },
            timeout=90
        )
        r.raise_for_status()
        answer = r.json()["choices"][0]["message"]["content"]
        answer += f"\n\nSources: {', '.join(sources)}"

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": f"Backend error: {e}"}), 500


# ========== STATIC CHAT PAGE (OPTIONAL IN CASE YOU USE IT) ==========
@app.route("/chat")
def chat_page():
    return send_from_directory("static", "chat.html")


# ========== FILE UPLOAD ==========
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files uploaded"}), 400

        for f in request.files.getlist("files"):
            save_path = os.path.join("uploads", f.filename)
            f.save(save_path)

        return jsonify({"status": "uploaded"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== REINDEX ==========
@app.route("/reindex", methods=["POST"])
def reindex():
    try:
        embed_and_store()
        uploaded_files = os.listdir("uploads")
        return jsonify({"status": "reindexed", "files": uploaded_files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== LIST FILES ==========
@app.route("/files", methods=["GET"])
def list_files():
    try:
        files = os.listdir("uploads")
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== Uploader UI ==========
@app.route("/uploader")
def uploader():
    return send_from_directory("static", "upload.html")


# ========== SERVER BOOT ==========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
