import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from crawler_controller import CrawlerManager, register_crawler_routes

# ----------------------------------------------------
# Flask Application Setup
# ----------------------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Initialize crawler manager and register routes
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# ----------------------------------------------------
# Paths & Directories
# ----------------------------------------------------
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------------------------------------------
# Root Route
# ----------------------------------------------------
@app.route("/")
def home():
    return """
        <h2>🚀 Novacool RAG Deployment Active</h2>
        <p>Visit:</p>
        <ul>
          <li><a href="/uploader">/uploader</a> – Upload & Crawl Dashboard</li>
          <li><a href="/chat">/chat</a> – Chatbot Interface</li>
          <li><a href="/widget">/widget</a> – Embeddable Widget</li>
        </ul>
    """

# ----------------------------------------------------
# File Upload Endpoint
# ----------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(save_path)
    return jsonify({"message": f"✅ {file.filename} uploaded successfully."})

# ----------------------------------------------------
# Knowledge Base Reindex Placeholder
# (You can expand this to trigger real reindexing)
# ----------------------------------------------------
def reindex_knowledge_base():
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    if not os.path.exists(kb_path):
        open(kb_path, "w", encoding="utf-8").close()
    return "Reindex complete ✅"

@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"message": msg})

# ----------------------------------------------------
# Serve Uploader Page
# ----------------------------------------------------
@app.route("/uploader")
def uploader():
    return send_from_directory("templates", "uploader.html")

# ----------------------------------------------------
# Serve Chat / Widget Placeholders
# (You can later replace these with your full chat UI)
# ----------------------------------------------------
@app.route("/chat")
def chat():
    return "<h3>🧠 Chat Interface coming soon</h3>"

@app.route("/widget")
def widget():
    return "<h3>💬 Widget Embed coming soon</h3>"

# ----------------------------------------------------
# Real-Time Crawler Status (for front-end polling)
# ----------------------------------------------------
@app.route("/crawler_status")
def crawler_status():
    return jsonify({
        "active": crawler.active,
        "paused": crawler.paused,
        "stopped": crawler.stopped,
        "progress": crawler.progress,
        "status": crawler.status
    })

# ----------------------------------------------------
# Run Application
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
