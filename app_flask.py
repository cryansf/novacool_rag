import os
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from rag_pipeline import answer_query, run_reindex

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ===========================
# HEALTH CHECK
# ===========================
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ===========================
# CHAT ENDPOINT
# ===========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "⚠️ No question received."})

    try:
        reply = answer_query(question)
        return jsonify({"answer": reply})
    except Exception as e:
        return jsonify({"answer": f"Error: {str(e)}"})

# ===========================
# LIST INDEXED FILENAMES
# ===========================
@app.route("/files")
def list_files():
    try:
        df = pd.read_csv("data/metadata.csv")
        files = sorted(set(df["source"].tolist()))
        return jsonify({"files": files})
    except Exception:
        return jsonify({"files": []})

# ===========================
# FILE UPLOAD
# ===========================
@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"status": "No files uploaded"})
    
    for file in request.files.getlist("files"):
        file.save(os.path.join(UPLOAD_DIR, file.filename))

    return jsonify({"status": "Upload complete — you may now click REINDEX"})

# ===========================
# REINDEX
# ===========================
@app.route("/reindex", methods=["POST"])
def reindex():
    try:
        run_reindex()
        return jsonify({"status": "Reindexing complete!"})
    except Exception as e:
        return jsonify({"status": f"Reindex error: {str(e)}"})

# ===========================
# WIDGET + CHAT UI PAGES
# ===========================
@app.route("/")
def root():
    return render_template("chat.html")

@app.route("/widget")
def widget():
    return send_from_directory("static", "widget.html")

# ===========================
# REQUIRED ENTRYPOINT
# (Render will ignore this when using Gunicorn)
# ===========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
