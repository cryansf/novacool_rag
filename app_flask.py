import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rag_pipeline import embed_and_store, search_vector_store

app = Flask(__name__)
CORS(app)

CHAT_MODEL = "gpt-4o-mini"

@app.route("/health")
def health():
    return "OK", 200

@app.route("/chat", methods=["POST"])
def chat_api():
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
                    {"role":"system","content": "You are Novacool’s assistant. Cite filenames."},
                    {"role":"user","content": f"Context:\n{context}\n\nQuestion: {question}"}
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

@app.route("/upload", methods=["POST"])
def upload_api():
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files uploaded"}), 400
        for f in request.files.getlist("files"):
            f.save(os.path.join("uploads", f.filename))
        return jsonify({"status": "uploaded"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reindex", methods=["POST"])
def reindex_api():
    try:
        embed_and_store()
        return jsonify({"status": "reindexed", "files": os.listdir("uploads")}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/files", methods=["GET"])
def list_files_api():
    try:
        return jsonify(os.listdir("uploads"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/uploader")
def uploader_page():
    return send_from_directory("static", "upload.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
