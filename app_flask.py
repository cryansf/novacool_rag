from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from crawler_controller import CrawlerManager, register_crawler_routes

# --- App setup ---
app = Flask(__name__)
CORS(app)
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# --- Paths (Persistent Disk) ---
DATA_DIR = "/opt/render/project/data"   # Persistent disk mount
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Startup log verification ---
try:
    existing_files = os.listdir(UPLOAD_FOLDER)
    file_count = len(existing_files)
    print(f"✅ Using persistent data directory: {DATA_DIR}")
    print(f"📁 Upload folder verified: {UPLOAD_FOLDER}")
    if file_count > 0:
        print(f"📦 Found {file_count} file(s) in uploads: {', '.join(existing_files[:5])}{' ...' if file_count > 5 else ''}")
    else:
        print("📭 No files found in uploads yet.")
except Exception as e:
    print(f"⚠️ Warning: Could not verify uploads folder — {e}")

# --- Routes ---

@app.route("/")
def home():
    return "<h2>Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

# --- Upload endpoint ---
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    print(f"📤 Uploaded: {file.filename} -> {path}")

    # Append to knowledge base placeholder
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    with open(kb_path, "a", encoding="utf-8") as kb:
        kb.write(f"\nFile uploaded: {file.filename}")
    print(f"📘 Added {file.filename} to knowledge base log.")

    return jsonify({"message": f"{file.filename} uploaded and added to knowledge base."})

# --- Manual reindex endpoint ---
@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"message": msg})

def reindex_knowledge_base():
    return "Reindex complete (stub)."

# --- Serve uploader page ---
@app.route("/uploader")
def uploader():
    return send_from_directory("templates", "uploader.html")

# --- Crawler status endpoint ---
@app.route("/crawler_status")
def crawler_status():
    return jsonify({
        "active": crawler.active,
        "paused": crawler.paused,
        "stopped": crawler.stopped,
        "progress": crawler.progress,
        "status": crawler.status
    })

# --- Persistent disk status check ---
@app.route("/status")
def status():
    """Return JSON summary of data folder and uploads."""
    try:
        files = os.listdir(UPLOAD_FOLDER)
        file_count = len(files)
        return jsonify({
            "data_dir": DATA_DIR,
            "upload_folder": UPLOAD_FOLDER,
            "file_count": file_count,
            "files": files[:10],  # Show only first 10 for brevity
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Main ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
