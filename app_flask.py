import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from rag_pipeline import (
    add_files_to_knowledge_base,
    reindex_knowledge_base,
    retrieve_relevant_chunks
)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@app.route("/")
def index():
    return "Novacool AI backend running.", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/chat")
def chat_page():
    return render_template("chat.html")


@app.route("/uploader")
def uploader_page():
    return render_template("uploader.html")


@app.route("/upload_files", methods=["POST"])
def upload_files():
    try:
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files provided"}), 400

        add_files_to_knowledge_base(files)
        return jsonify({"status": "Files uploaded successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reindex", methods=["POST"])
def reindex():
    try:
        reindex_knowledge_base()
        return jsonify({"status": "Knowledge base reindexed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ask", methods=["POST"])
def ask():
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500

        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()
        if not question:
            return jsonify({"error": "No question provided"}), 400

        # Retrieve relevant text chunks from embeddings
        context = retrieve_relevant_chunks(question, top_k=6)
        if not context:
            context = "No relevant context retrieved from Novacool documents."

        # Build prompt with retrieved context
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
                        "You are Novacool AI, an expert assistant for SW Firefighting Foam & Equipment. "
                        "Base your answers ONLY on the Novacool documentation provided in context. "
                        "Never guess — if information is not present, say so."
                    )
                },
                {
                    "role": "assistant",
                    "content": f"Relevant information from Novacool knowledge base:\n\n{context}"
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
            "temperature": 0.25
        }

        r = requests.post(url, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        reply = r.json()["choices"][0]["message"]["content"].strip()
        return jsonify({"answer": reply}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
