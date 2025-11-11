from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from crawler_controller import crawl_and_ingest

# --- Flask setup ---
app = Flask(__name__)
CORS(app)

# --- Persistent Data Paths ---
DATA_DIR = "/opt/render/project/data"
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Crawler Setup ---
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# -------------------------------------------------
# BASE ROUTES
# -------------------------------------------------
@app.route("/")
def home():
    return "<h2>Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

@app.route("/uploader")
def uploader_page():
    return send_from_directory("templates", "uploader.html")

# -------------------------------------------------
# UPLOAD ROUTES
# -------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload endpoint for PDF, DOCX, or TXT."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save file
    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)

    # Add file info to knowledge base
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    with open(kb_path, "a", encoding="utf-8") as kb:
        kb.write(f"{file.filename}\n")

    return jsonify({"message": f"✅ {file.filename} uploaded and added to knowledge base."}), 200

@app.route("/uploads", methods=["GET"])
def list_uploads():
    """List files stored persistently."""
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify({"files": files, "count": len(files)})

# -------------------------------------------------
# REINDEX (STUB)
# -------------------------------------------------
@app.route("/reindex", methods=["POST"])
def reindex_knowledge_base():
    """Placeholder for reindex operation."""
    return jsonify({"message": "Reindex complete (stub)."}), 200

# -------------------------------------------------
# CRAWLER CONTROL ROUTES
# -------------------------------------------------
@app.route("/start_crawl", methods=["POST"])
def start_crawl():
    """Start a new crawl."""
    data = request.get_json()
    base_url = data.get("url")
    if not base_url:
        return jsonify({"error": "Missing base URL"}), 400

    try:
        crawler.start(base_url)
        return jsonify({"message": f"Crawl started for {base_url}."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/pause_crawl", methods=["GET"])
def pause_crawl():
    """Pause the ongoing crawl."""
    crawler.pause()
    return jsonify({"message": "Crawl paused."}), 200

@app.route("/stop_crawl", methods=["GET"])
def stop_crawl():
    """Stop the ongoing crawl."""
    crawler.stop()
    return jsonify({"message": "Crawl stopped."}), 200

@app.route("/crawler_status", methods=["GET"])
def crawler_status():
    """Return JSON with the crawler's current state."""
    return jsonify({
        "active": crawler.active,
        "paused": crawler.paused,
        "stopped": crawler.stopped,
        "progress": crawler.progress,
        "status": crawler.status
    })

# -------------------------------------------------
# SERVE FILES AND CHAT ENDPOINTS
# -------------------------------------------------
@app.route("/chat")
def chat_page():
    return send_from_directory("templates", "chat.html")

@app.route("/widget")
def widget_page():
    return send_from_directory("templates", "widget.html")

# -------------------------------------------------
# ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
