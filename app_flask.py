import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rag_pipeline import answer_query, run_reindex

app = Flask(__name__)
CORS(app)


# ---------- HEALTH ----------
@app.route("/health")
def health():
    return "OK", 200


# ---------- CHAT (QUESTION ANSWERING) ----------
@app.route("/chat", methods=["POST"])
def chat_api():
    try:
        question = request.json.get("question", "").strip()
        if not question:
            return jsonify({"error": "No question provided"}), 400

        answer = answer_query(question)
        return jsonify({"answer": answer}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- FILE UPLOAD ----------
@app.route("/upload", methods=["POST"])
def upload_api():
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files uploaded"}), 400

        for f in request.files.getlist("files"):
            save_path = os.path.join("uploads", f.filename)
            f.save(save_path)

        return jsonify({"status": "uploaded"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- REINDEX ----------
@app.route("/reindex", methods=["POST"])
def reindex_api():
    try:
        result = run_reindex()         # ⚡ calls the real function in rag_pipeline.py
        return jsonify({"status": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- LIST FILES ----------
@app.route("/files", methods=["GET"])
def list_files_api():
    try:
        return jsonify(os.listdir("uploads")), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- STATIC UPLOADER DASHBOARD ----------
@app.route("/uploader")
def uploader_page():
    return send_from_directory("static", "upload.html")


# ---------- SERVER ENTRY ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
