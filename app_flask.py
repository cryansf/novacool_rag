from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os

# Import modules
from crawler_controller import crawl_and_ingest
from rag_pipeline import ingest_text, search_docs

# -----------------------------------------------------------------------------
# Flask App Setup
# -----------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# Persistent folder (Render’s /data is preserved across deploys)
UPLOAD_FOLDER = "/data/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------------------------------------------------------
# Root - Uploader Page
# -----------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def uploader_page():
    """Serve the Bootstrap uploader interface."""
    return render_template("uploader.html")

# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})

# -----------------------------------------------------------------------------
# Upload File
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Serve Uploaded Files
# -----------------------------------------------------------------------------
@app.route("/uploads/<path:filename>", methods=["GET"])
def get_uploaded_file(filename):
    """Allow access to previously uploaded files."""
    return send_from_directory(UPLOAD_FOLDER, filename)

# -----------------------------------------------------------------------------
# List All Uploaded Files
# -----------------------------------------------------------------------------
@app.route("/check_uploads", methods=["GET"])
def check_uploads():
    """List all files currently stored in /data/uploads."""
    try:
        files = os.listdir(UPLOAD_FOLDER)
        file_urls = [f"/uploads/{name}" for name in files]
        return jsonify({"files": file_urls})
    except Exception as e:
        return jsonify({"error": f"Unable to list uploads: {e}"}), 500

# -----------------------------------------------------------------------------
# Crawl and Ingest Endpoint
# -----------------------------------------------------------------------------
@app.route("/crawl", methods=["POST"])
def crawl_route():
    """Crawl a webpage and ingest its text into the RAG pipeline."""
    data = request.get_json()
    url = data.get("url") if data else None

    if not url:
        return jsonify({"error": "Missing 'url' in request body"}), 400

    result = crawl_and_ingest(url)
    return jsonify({"message": result})

# -----------------------------------------------------------------------------
# Chat / Query Endpoint (with placeholder reply)
# -----------------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """
    Accept JSON: {"query": "<user question>"}
    Returns a simulated response now, real RAG search later.
    """
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    # Placeholder reply to confirm chat works
    return jsonify({
        "query": query,
        "message": f"🤖 Thanks for your question: '{query}'. I'm connected to the Novacool RAG backend and ready for full AI responses soon!"
    }), 200

# -----------------------------------------------------------------------------
# Main Entry
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
