from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from crawler_controller import CrawlerManager, register_crawler_routes

# --- Setup ---
app = Flask(__name__)
CORS(app)
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# --- Directories ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "index"), exist_ok=True)

# --- Helper: auto-load uploaded docs into knowledge base ---
def load_uploaded_files_to_kb():
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    if not os.path.exists(kb_path):
        open(kb_path, "w").close()

    appended = 0
    for fname in os.listdir(UPLOAD_DIR):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        ext = fname.lower().split(".")[-1]
        if ext not in ["pdf", "docx", "txt"]:
            continue
        with open(kb_path, "a", encoding="utf-8", errors="ignore") as kb:
            kb.write(f"\n--- Imported: {fname} ---\n")
            kb.write(f"[Placeholder text extracted from {fname}]\n")
        appended += 1
    return appended

# Run on startup
appended_count = load_uploaded_files_to_kb()
print(f"📚 Knowledge base initialized. {appended_count} files added from /uploads.")

# --- Routes ---
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
    return "<h3>Novacool widget active — embedded chat endpoint working.</h3>"

# --- File upload ---
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(save_path)

    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    with open(kb_path, "a", encoding="utf-8") as kb:
        kb.write(f"\n--- Uploaded: {file.filename} ---\n[Placeholder content added]\n")

    return jsonify({"message": f"✅ {file.filename} uploaded and added to knowledge base."})

# --- Reindex Knowledge Base (stub) ---
def reindex_knowledge_base():
    kb_path = os.path.join(DATA_DIR, "knowledge_base.txt")
    with open(kb_path, "a", encoding="utf-8") as kb:
        kb.write("\n(Reindex called — placeholder)\n")
    return "Reindex complete (stub)."

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

    reply = f"Novacool Assistant: You said '{user_msg}'. (RAG response placeholder)"
    return jsonify({"reply": reply})

# --- Serve data files ---
@app.route("/data/<path:filename>")
def serve_data(filename):
    return send_from_directory(DATA_DIR, filename)

# --- Fixed JSON crawler endpoints ---
@app.route("/crawler/start")
def crawler_start():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "Missing URL"}), 400
    msg = crawler.start(url)
    return jsonify({"message": msg})

@app.route("/crawler/pause")
def crawler_pause():
    msg = crawler.pause()
    return jsonify({"message": msg})

@app.route("/crawler/stop")
def crawler_stop():
    msg = crawler.stop()
    return jsonify({"message": msg})

@app.route("/crawler_status")
def crawler_status():
    return jsonify({
        "active": crawler.active,
        "paused": crawler.paused,
        "stopped": crawler.stopped,
        "progress": crawler.progress,
        "status": crawler.status
    })

# --- Run ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
