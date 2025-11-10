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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- ROUTES ---

@app.route("/")
def home():
    return "<h2>Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

@app.route("/uploader")
def uploader():
    return send_from_directory("templates", "uploader.html")

@app.route("/chat")
def chat():
    return send_from_directory("templates", "chat.html")

@app.route("/widget")
def widget():
    return "<h3>Novacool widget active — endpoint will serve the embedded chat.</h3>"

# --- Upload documents ---
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)
    return jsonify({"message": f"✅ {file.filename} uploaded successfully!"})

# --- Reindex Knowledge Base (stub) ---
def reindex_knowledge_base():
    # Placeholder — in a full system this would rebuild embeddings.
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    manifest_path = os.path.join(DATA_DIR, "manifest.json")
    os.makedirs(os.path.join(DATA_DIR, "index"), exist_ok=True)

    with open(kb_path, "a") as kb:
        kb.write("\n(Reindex called — placeholder)\n")

    with open(manifest_path, "w") as mf:
        mf.write('{"manifest": "updated"}')

    return "Reindex complete (stub)"

@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"message": msg})

# --- Chat API ---
@app.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.get_json()
    user_msg = data.get("message", "")
    if not user_msg:
        return jsonify({"error": "No message provided"}), 400

    # Placeholder AI logic — replace with actual RAG model call.
    reply = f"Novacool Assistant: You said '{user_msg}'. (RAG response placeholder)"
    return jsonify({"reply": reply})

# --- Serve static data files ---
@app.route("/data/<path:filename>")
def serve_data(filename):
    return send_from_directory(DATA_DIR, filename)

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

# --- Run locally ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
