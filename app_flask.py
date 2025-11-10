from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from crawler_controller import CrawlerManager, register_crawler_routes

# --- App setup ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Initialize crawler ---
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# --- Paths ---
DATA_DIR = "/opt/render/project/data"  # Persistent disk mount
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Home route ---
@app.route("/")
def home():
    return "<h2>🔥 Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

# --- File upload handler ---
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        # Handle multiple file uploads
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files uploaded"}), 400

        saved_files = []
        for file in files:
            if file.filename:
                save_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(save_path)
                saved_files.append(file.filename)

        return jsonify({"status": f"✅ {len(saved_files)} file(s) uploaded successfully."})

    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

# --- Reindex placeholder ---
def reindex_knowledge_base():
    """
    Stub for future vector DB or LangChain integration.
    You can call this from crawler_controller after crawling completes.
    """
    return "Reindex complete (stub)."

@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"message": msg})

# --- Serve uploader HTML page ---
@app.route("/uploader")
def uploader():
    """
    Serves the uploader dashboard.
    Must have 'templates/uploader.html' present.
    """
    return send_from_directory("templates", "uploader.html")

# --- Crawl status (used by JS progress logger) ---
@app.route("/crawl_status")
def crawl_status():
    """Status endpoint polled by uploader frontend"""
    try:
        return jsonify({
            "active": crawler.active,
            "paused": crawler.paused,
            "stopped": crawler.stopped,
            "progress": crawler.progress,
            "status": crawler.status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Health check route ---
@app.route("/status")
def status():
    return jsonify({
        "status": "online",
        "message": "Novacool RAG backend responding",
        "crawler_active": crawler.active,
        "files_in_uploads": len(os.listdir(UPLOAD_FOLDER))
    })

# --- Run app ---
if __name__ == "__main__":
    print("🚀 Starting Novacool RAG Flask Server on port 8080...")
    app.run(host="0.0.0.0", port=8080)
