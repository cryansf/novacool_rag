from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from crawler_controller import CrawlerManager, register_crawler_routes

# --- App setup ---
app = Flask(__name__)
CORS(app)

# --- Initialize crawler ---
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# --- Directory setup ---
DATA_DIR = "data"
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
INDEX_DIR = os.path.join(DATA_DIR, "index")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")
KB_PATH = os.path.join(DATA_DIR, "knowledge_base.txt")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# --- Root route ---
@app.route("/")
def home():
    return """
    <h2>Novacool RAG Deployment Active 🚀</h2>
    <ul>
      <li><a href="/uploader">📁 Uploader Dashboard</a></li>
      <li><a href="/chat">💬 Novacool Assistant Chat</a></li>
      <li><a href="/widget">🔌 Widget Test</a></li>
    </ul>
    """

# --- File Upload ---
@app.route("/upload", methods=["POST"])
def upload_files():
    """
    Accept multiple files (.pdf, .docx, .txt) and save them under /data/uploads.
    """
    if "files" not in request.files:
        return jsonify({"error": "No files part in request"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    uploaded = []
    for file in files:
        filename = file.filename.strip()
        if not filename:
            continue
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        uploaded.append(filename)

    return jsonify({"status": f"{len(uploaded)} file(s) uploaded successfully.", "files": uploaded})

# --- Simple Reindex (stub for now) ---
def reindex_knowledge_base():
    """
    Stub reindex function — you can later extend this to regenerate embeddings.
    """
    if not os.path.exists(KB_PATH):
        open(KB_PATH, "a").close()
    return "Reindex complete (stub)."

@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"status": msg})

# --- Serve Templates ---
@app.route("/uploader")
def uploader():
    return send_from_directory("templates", "uploader.html")

@app.route("/chat")
def chat():
    return send_from_directory("templates", "chat.html")

@app.route("/widget")
def widget():
    return "<h3>Novacool widget Active — endpoint serving embedded chat widget</h3>"

# --- Serve Uploaded Files ---
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# --- Crawler Status Endpoint ---
@app.route("/crawler_status")
def crawler_status():
    return jsonify({
        "active": crawler.active,
        "paused": crawler.paused,
        "stopped": crawler.stopped,
        "progress": crawler.progress,
        "status": crawler.status
    })

# --- Health Check ---
@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "Novacool Flask app running"}), 200

# --- Run app ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
