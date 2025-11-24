import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

from rag_pipeline import run_rag_pipeline, reindex_all

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==========================
# 🔥  CHAT UI  (GET)
# ==========================
@app.route("/chat", methods=["GET"])
def chat_ui():
    """
    Load chat page for browser (used by widget iframe)
    """
    return render_template("chat.html")


# ==========================
# 🤖  CHAT API (POST)
# ==========================
@app.route("/chat", methods=["POST"])
def chat_api():
    """
    Accepts a user question and returns an AI answer
    """
    data = request.json
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "I didn't receive a question."})

    answer = run_rag_pipeline(question)
    return jsonify({"answer": answer})


# ==========================
# 📁  PRIVATE UPLOADER PAGE (GET)
# ==========================
@app.route("/uploader", methods=["GET"])
def uploader_page():
    """
    Admin-only dashboard to upload and reindex files
    """
    return render_template("upload.html")


# ==========================
# ⬆  FILE UPLOAD HANDLER (POST)
# ==========================
@app.route("/upload", methods=["POST"])
def upload_files():
    """
    Upload PDFs, DOCX, TXT, HTML, etc. and store in persistent uploads folder
    """
    if "files" not in request.files:
        return jsonify({"status": "No files received"})

    files = request.files.getlist("files")
    saved = []

    for f in files:
        filename = secure_filename(f.filename)
        save_path = os.path.join(UPLOAD_DIR, filename)
        f.save(save_path)
        saved.append(filename)

    return jsonify({"status": f"{len(saved)} files uploaded", "files": saved})


# ==========================
# 🔄  REINDEX KNOWLEDGE BASE (POST)
# ==========================
@app.route("/reindex", methods=["POST"])
def reindex():
    """
    Rebuild FAISS + embeddings from all uploaded files
    """
    try:
        count = reindex_all()
        return jsonify({"status": f"Reindex complete — {count} documents processed"})
    except Exception as e:
        return jsonify({"status": f"Reindex failed: {str(e)}"}), 500


# ==========================
# ❤️  HEALTH CHECK
# ==========================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "OK"})


# ==========================
# 🚀  MAIN
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
