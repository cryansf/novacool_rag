import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rag_pipeline import add_files_to_knowledge_base, reindex_knowledge_base, answer_query

app = Flask(__name__)
CORS(app)

# ===== Correct persistent storage directories on your Render service =====
UPLOAD_DIR = "/opt/render/project/src/uploads"
DATA_DIR = "/opt/render/project/src/data"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    question = (data.get("query") or "").strip()
    if not question:
        return jsonify({"response": "Please enter a question."})
    try:
        answer = answer_query(question)
        return jsonify({"response": answer})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500


@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"message": "No files received"}), 400
    files = request.files.getlist("files")
    add_files_to_knowledge_base(files)
    return jsonify({"message": f"{len(files)} file(s) uploaded successfully"})


@app.route("/reindex", methods=["GET"])
def reindex():
    try:
        reindex_knowledge_base()
        return jsonify({"message": "Reindex complete"})
    except Exception as e:
        return jsonify({"message": f"Reindex failed — {str(e)}"}), 500


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)


@app.route("/")
def root():
    return "Novacool RAG backend running"
