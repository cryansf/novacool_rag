from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from crawler_controller import CrawlerManager, register_crawler_routes

# --- App setup ---
app = Flask(__name__)
CORS(app)
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# --- Paths ---
DATA_DIR = "data"
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def home():
    return "<h2>Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

# --- File upload ---
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    return jsonify({"message": f"{file.filename} uploaded successfully."})

# --- Simple reindex placeholder (stub for now) ---
def reindex_knowledge_base():
    return "Reindex complete (stub)."

@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"message": msg})

# --- Serve uploader page ---
@app.route("/uploader")
def uploader():
    return send_from_directory("templates", "uploader.html")

# --- Polling endpoint for JS ---
@app.route("/crawler_status")
def crawler_status():
    return jsonify({
        "active": crawler.active,
        "paused": crawler.paused,
        "stopped": crawler.stopped,
        "progress": crawler.progress,
        "status": crawler.status
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
