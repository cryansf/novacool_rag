import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_pipeline import answer_query, run_reindex

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==========================
# HEALTH CHECK
# ==========================
@app.route("/health")
def health():
    return "OK", 200


# ==========================
# MAIN CHAT ENDPOINT
# ==========================
@app.route("/chat", methods=["POST"])
def chat_api():
    try:
        question = request.json.get("question", "").strip()
        if not question:
            return jsonify({"error": "No question provided"}), 400

        answer = answer_query(question)
        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": f"Backend error: {e}"}), 500


# ==========================
# UPLOAD DOCUMENTS
# ==========================
@app.route("/upload", methods=["POST"])
def upload_files():
    """Save uploaded files into /uploads directory."""
    if "files" not in request.files:
        return jsonify({"error": "No files received"}), 400

    for f in request.files.getlist("files"):
        f.save(os.path.join(UPLOAD_DIR, f.filename))

    return jsonify({"message": "Files uploaded successfully."})


# ==========================
# REBUILD EMBEDDINGS
# ==========================
@app.route("/reindex", methods=["POST"])
def reindex_route():
    """Rebuild FAISS + metadata from uploaded files."""
    message = run_reindex()
    return jsonify({"message": message})


# ==========================
# LIST STORED FILES
# ==========================
@app.route("/files", methods=["GET"])
def list_files():
    files = os.listdir(UPLOAD_DIR)
    return jsonify({"files": files})


# ==========================
# MAIN ENTRY
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
