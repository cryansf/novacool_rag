from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import time

# ---------------------------------------------------------------------------
# Flask Setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "/data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CRAWL_LOG_PATH = "/data/crawler.log"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def uploader_page():
    """Serve the main interface with uploader, crawler, and chat."""
    return render_template("uploader.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# -------------------------- File Uploading --------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file uploads."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        save_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(save_path)
        return jsonify({"message": f"File '{file.filename}' uploaded successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/uploads/<path:filename>", methods=["GET"])
def get_uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/check_uploads", methods=["GET"])
def check_uploads():
    """List uploaded files."""
    try:
        files = sorted(os.listdir(UPLOAD_FOLDER))
        file_urls = [f"/uploads/{name}" for name in files]
        return jsonify({"files": file_urls})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------- Simulated Crawler --------------------------
@app.route("/crawl", methods=["POST"])
def start_crawl():
    """Simulated crawler start."""
    data = request.get_json(force=True)
    url = data.get("url", "")
    with open(CRAWL_LOG_PATH, "a") as f:
        f.write(f"[{time.ctime()}] 🕷️ Crawl started for: {url}\n")
    return jsonify({"message": f"Crawl started for {url}"})


@app.route("/crawl/pause", methods=["POST"])
def pause_crawl():
    with open(CRAWL_LOG_PATH, "a") as f:
        f.write(f"[{time.ctime()}] ⏸️ Crawl paused\n")
    return jsonify({"message": "Crawler paused"})


@app.route("/crawl/stop", methods=["POST"])
def stop_crawl():
    with open(CRAWL_LOG_PATH, "a") as f:
        f.write(f"[{time.ctime()}] 🛑 Crawl stopped\n")
    return jsonify({"message": "Crawler stopped"})


@app.route("/crawl/clear", methods=["POST"])
def clear_logs():
    open(CRAWL_LOG_PATH, "w").close()
    return jsonify({"message": "Logs cleared"})


@app.route("/crawl/logs", methods=["GET"])
def get_logs():
    if not os.path.exists(CRAWL_LOG_PATH):
        return jsonify({"logs": ""})
    with open(CRAWL_LOG_PATH, "r") as f:
        logs = f.read()
    return jsonify({"logs": logs})


# -------------------------- Chat Endpoint --------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400
    # Simulated chat response
    return jsonify({"message": f"Hi Casey — I received: '{query}'. Live RAG integration coming soon!"})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
