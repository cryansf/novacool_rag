from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, time, json
from crawler_controller import CrawlerManager, register_crawler_routes

# ====================================================
# 🔧 Flask App Setup
# ====================================================
app = Flask(__name__)
CORS(app)

# ====================================================
# 📁 Directory Setup
# ====================================================
DATA_DIR = "data"
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
INDEX_DIR = os.path.join(DATA_DIR, "index")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# ====================================================
# 🧠 Knowledge Base Reindex Helper
# ====================================================
def reindex_knowledge_base():
    """
    Placeholder reindex function used by the crawler and /reindex route.
    You can replace this later with your FAISS / LangChain vector rebuild logic.
    """
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(kb_path, "a", encoding="utf-8") as f:
        f.write(f"\n[Auto-reindexed at {time.ctime()}]\n")
    print("✅ Knowledge base reindexed.")
    return "Knowledge base reindexed successfully."


# ====================================================
# 🕷 Initialize Crawler
# ====================================================
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# ====================================================
# 📦 Helper: Load Manifest
# ====================================================
def load_existing_hashes():
    manifest_path = os.path.join(DATA_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

# ====================================================
# 🌐 Routes
# ====================================================

@app.route("/")
def home():
    return "<h2>🔥 Novacool RAG Deployment Active</h2><p>Visit <a href='/uploader'>/uploader</a> to manage uploads & crawling.</p>"

# ----------------------------
# 📤 File Upload
# ----------------------------
@app.route("/upload", methods=["POST"])
def upload_files():
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    uploaded = []
    for file in request.files.getlist("files"):
        filename = file.filename
        if not filename:
            continue
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        uploaded.append(filename)

    return jsonify({"status": f"{len(uploaded)} file(s) uploaded successfully.", "files": uploaded})

# ----------------------------
# 🔁 Manual Reindex Route
# ----------------------------
@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"message": msg})

# ----------------------------
# 📥 Download Manifest
# ----------------------------
@app.route("/download_manifest")
def download_manifest():
    try:
        return send_from_directory(DATA_DIR, "manifest.json", as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------
# 📘 Download Knowledge Base
# ----------------------------
@app.route("/download_kb")
def download_kb():
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    if os.path.exists(kb_path):
        return send_from_directory(DATA_DIR, "knowledge_base.txt", as_attachment=True)
    return jsonify({"error": "Knowledge base not found"}), 404

# ----------------------------
# ⚙️ System Status
# ----------------------------
@app.route("/system_status")
def system_status():
    manifest = load_existing_hashes()
    index_path = os.path.join(INDEX_DIR, "faiss_index")
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")

    # calculate index size (MB)
    index_size_mb = 0
    if os.path.exists(index_path):
        for dirpath, _, filenames in os.walk(index_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                index_size_mb += os.path.getsize(fp)
        index_size_mb = round(index_size_mb / (1024 * 1024), 2)

    kb_exists = os.path.exists(kb_path)
    kb_mtime = time.ctime(os.path.getmtime(kb_path)) if kb_exists else "N/A"

    return jsonify({
        "indexed_files": len(manifest),
        "upload_dir_files": len(os.listdir(UPLOAD_FOLDER)),
        "index_size_mb": index_size_mb,
        "knowledge_base_exists": kb_exists,
        "last_reindex": kb_mtime,
        "crawler_active": crawler.active
    })

# ----------------------------
# 🧭 Serve Dashboard
# ----------------------------
@app.route("/uploader")
def uploader():
    return send_from_directory("templates", "uploader.html")

# ====================================================
# 📤 Export symbols for crawler import
# ====================================================
__all__ = ["reindex_knowledge_base"]

# ====================================================
# 🚀 Main Entrypoint
# ====================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
