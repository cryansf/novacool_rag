from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import time
from threading import Thread

# --------------------------------------------------------------------------
# Flask Setup
# --------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# Persistent uploads directory (Render's /data survives redeploys)
UPLOAD_FOLDER = "/data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------------------------------------------
# Import stubs (these will later be replaced by your full RAG + crawler logic)
# --------------------------------------------------------------------------
from rag_pipeline import ingest_text, search_docs

# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

# Root → show uploader/crawler/chat dashboard
@app.route("/", methods=["GET"])
def uploader_page():
    return render_template("uploader.html")


# Health check
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


# --------------------------------------------------------------------------
# Upload Handling
# --------------------------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload and persist files into /data/uploads directory."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        save_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(save_path)
        return jsonify({
            "message": f"File '{file.filename}' saved successfully.",
            "path": f"/uploads/{file.filename}"
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {e}"}), 500


@app.route("/uploads/<path:filename>", methods=["GET"])
def get_uploaded_file(filename):
    """Allow access to previously uploaded files."""
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/check_uploads", methods=["GET"])
def check_uploads():
    """List all files currently stored in /data/uploads."""
    try:
        files = os.listdir(UPLOAD_FOLDER)
        file_urls = [f"/uploads/{name}" for name in files]
        return jsonify({"files": file_urls})
    except Exception as e:
        return jsonify({"error": f"Unable to list uploads: {e}"}), 500


# --------------------------------------------------------------------------
# Simulated Crawler Engine (fully functional for UI testing)
# --------------------------------------------------------------------------
crawl_state = {"active": False, "paused": False, "logs": []}

def crawl_job(url):
    """Simulated background crawl process."""
    crawl_state["logs"].append(f"🕷️ Starting crawl on {url}")
    for i in range(1, 11):
        if not crawl_state["active"]:
            crawl_state["logs"].append("❌ Crawl stopped.")
            return
        while crawl_state["paused"]:
            time.sleep(1)
        crawl_state["logs"].append(f"📄 Crawling page {i} of 10...")
        time.sleep(1.5)
    crawl_state["logs"].append("✅ Crawl complete.")
    crawl_state["active"] = False


@app.route("/start_crawl", methods=["POST"])
def start_crawl():
    data = request.get_json()
    url = data.get("url") if data else None
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400
    if crawl_state["active"]:
        return jsonify({"error": "Crawl already running"}), 400

    crawl_state["active"] = True
    crawl_state["paused"] = False
    crawl_state["logs"].clear()

    Thread(target=crawl_job, args=(url,), daemon=True).start()
    return jsonify({"message": f"Crawling started for {url}."})


@app.route("/pause_crawl", methods=["POST"])
def pause_crawl():
    if not crawl_state["active"]:
        return jsonify({"message": "No crawl running."})
    crawl_state["paused"] = not crawl_state["paused"]
    state = "paused" if crawl_state["paused"] else "resumed"
    crawl_state["logs"].append(f"⏸️ Crawl {state}.")
    return jsonify({"message": f"Crawl {state}."})


@app.route("/stop_crawl", methods=["POST"])
def stop_crawl():
    if not crawl_state["active"]:
        return jsonify({"message": "No crawl running."})
    crawl_state["active"] = False
    crawl_state["logs"].append("🛑 Crawl stopped by user.")
    return jsonify({"message": "Crawl stopped."})


@app.route("/crawl_status", methods=["GET"])
def crawl_status():
    """Return the current crawl log output."""
    return jsonify({"logs": crawl_state["logs"][-100:]})


# --------------------------------------------------------------------------
# Chat / Query Endpoint (basic placeholder)
# --------------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """Accept JSON { 'query': '...' } and perform RAG search."""
    data = request.get_json()
    query = data.get("query", "").strip() if data else ""
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    try:
        # Placeholder RAG result
        results = [{"text": "This is placeholder context until RAG indexing is live."}]
        return jsonify({"query": query, "results": results})
    except Exception as e:
        return jsonify({"error": f"RAG search failed: {e}"}), 500


# --------------------------------------------------------------------------
# Debug route
# --------------------------------------------------------------------------
@app.route("/debug", methods=["GET"])
def debug():
    return jsonify({
        "routes": [str(r) for r in app.url_map.iter_rules()],
        "upload_folder": UPLOAD_FOLDER,
        "files_present": os.listdir(UPLOAD_FOLDER)
    })


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
