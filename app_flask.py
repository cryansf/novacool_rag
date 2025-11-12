# app_flask.py
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os

# Local imports
from crawler_controller import crawl_and_ingest
from rag_pipeline import ingest_text, search_docs

app = Flask(__name__)
CORS(app)

# Persistent storage path (Render's /data is persistent)
UPLOAD_FOLDER = "/data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------
# ROOT: Main control console (Uploader + Crawler + Chat)
# ---------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("uploader.html")

# ---------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# ---------------------------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------------------------
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

        # Optional: auto-ingest text from PDF/DOCX after upload
        ingest_text(save_path)

        return jsonify({
            "message": f"File '{file.filename}' uploaded and indexed.",
            "path": f"/uploads/{file.filename}"
        }), 200
    except Exception as e:
        return jsonify({"error": f"Upload failed: {e}"}), 500

# ---------------------------------------------------------------------
# SERVE UPLOADED FILES
# ---------------------------------------------------------------------
@app.route("/uploads/<path:filename>", methods=["GET"])
def get_uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ---------------------------------------------------------------------
# LIST UPLOADED FILES
# ---------------------------------------------------------------------
@app.route("/check_uploads", methods=["GET"])
def check_uploads():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        file_urls = [f"/uploads/{name}" for name in files]
        return jsonify({"files": file_urls})
    except Exception as e:
        return jsonify({"error": f"Unable to list uploads: {e}"}), 500

# ---------------------------------------------------------------------
# CRAWLER: crawl and ingest
# ---------------------------------------------------------------------
@app.route("/crawl", methods=["POST"])
def crawl_route():
    data = request.get_json()
    url = data.get("url") if data else None
    if not url:
        return jsonify({"error": "Missing 'url' in request body"}), 400

    try:
        result = crawl_and_ingest(url)
        return jsonify({"message": result}), 200
    except Exception as e:
        return jsonify({"error": f"Crawler failed: {e}"}), 500

# ---------------------------------------------------------------------
# CHAT ENDPOINT
# ---------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """Perform semantic search and respond from indexed data."""
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400

    try:
        results = search_docs(query)
        return jsonify({
            "message": f"Found {len(results)} matching items.",
            "query": query,
            "results": results
        })
    except Exception as e:
        return jsonify({"error": f"Search failed: {e}"}), 500

# ---------------------------------------------------------------------
# WIDGET: embedded mini-chat (for GetResponse)
# ---------------------------------------------------------------------
@app.route("/widget", methods=["GET"])
def widget():
    return render_template("widget.html")

# ---------------------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
