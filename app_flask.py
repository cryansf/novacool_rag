import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from rag_pipeline import answer_query, run_reindex

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app)


# ------------------------ HEALTH ------------------------
@app.route("/health")
def health():
    return "OK", 200


# ------------------------ CHAT API ------------------------
@app.route("/chat", methods=["POST"])
def chat_api():
    try:
        data = request.json
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"answer": "⚠️ No question received"}), 200

        answer = answer_query(question)
        return jsonify({"answer": answer}), 200

    except Exception as e:
        return jsonify({"answer": f"⚠️ Backend error: {e}"}), 200


# ------------------------ UPLOADER PAGE ------------------------
@app.route("/uploader")
def uploader_page():
    return send_from_directory("static", "uploader.html")


# ------------------------ FILE UPLOAD ------------------------
@app.route("/upload", methods=["POST"])
def upload_files():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"message": "⚠️ No files received"}), 400

    for f in files:
        f.save(os.path.join(UPLOAD_DIR, f.filename))

    return jsonify({"message": f"{len(files)} file(s) uploaded successfully"}), 200


# ------------------------ FILE LIST ------------------------
@app.route("/files")
def list_uploaded_files():
    items = os.listdir(UPLOAD_DIR)
    return jsonify({"files": items})


# ------------------------ REINDEX ------------------------
@app.route("/reindex", methods=["POST"])
def reindex_api():
    msg = run_reindex()
    return jsonify({"message": msg})


# ------------------------ LAUNCH ------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
