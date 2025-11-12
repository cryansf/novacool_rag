# app_flask.py
import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from rag_pipeline import ingest_text, query_text  # your existing RAG utilities
from crawler_engine import crawl_and_ingest       # NEW autonomous crawler

app = Flask(__name__)

# Persistent upload directory
UPLOAD_DIR = "/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------------------------------------------------
# BASIC ROUTES
# --------------------------------------------------------------------
@app.route("/")
def uploader_page():
    """Main RAG Control Console (Uploader, Crawler, Chat Panels)."""
    return render_template("uploader.html")


@app.route("/widget")
def chat_widget():
    """Embeddable iframe widget for external sites (e.g. GetResponse)."""
    return render_template("widget.html")


@app.route("/health")
def health_check():
    return jsonify({"status": "ok"})


# --------------------------------------------------------------------
# FILE UPLOAD / MANAGEMENT
# --------------------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    """Handles manual PDF/DOCX upload and ingestion."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    # Ingest immediately into the RAG index
    try:
        result = ingest_text(save_path)
        message = f"File '{filename}' uploaded and indexed successfully."
        return jsonify({"message": message, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/uploads/<path:filename>")
def get_uploaded_file(filename):
    """Serve uploaded file directly from persistent storage."""
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/check_uploads")
def check_uploads():
    """Returns list of uploaded files."""
    files = sorted(os.listdir(UPLOAD_DIR))
    file_urls = [f"/uploads/{f}" for f in files]
    return jsonify({"files": file_urls})


# --------------------------------------------------------------------
# AUTONOMOUS CRAWLER
# --------------------------------------------------------------------
@app.route("/crawl", methods=["POST"])
def crawl():
    """Autonomous crawler that finds and indexes linked PDFs/DOCX from a URL."""
    data = request.get_json()
    base_url = data.get("url")
    if not base_url:
        return jsonify({"error": "Missing URL."}), 400

    try:
        logs = crawl_and_ingest(base_url)
        return jsonify({"message": "Crawl complete", "logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------------------------
# CHAT / QUERY ENDPOINT
# --------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """Handles semantic search / question answering queries."""
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query is empty."}), 400

    try:
        results = query_text(query)  # returns list of (filename, excerpt, score)
        if not results:
            return jsonify({"message": "No matches found.", "results": []})

        formatted = []
        for r in results:
            # RAG pipeline returns (filename, excerpt, score)
            formatted.append({
                "file": os.path.basename(r[0]),
                "excerpt": r[1][:500] + ("..." if len(r[1]) > 500 else "")
            })

        return jsonify({
            "message": f"Found {len(formatted)} matching items.",
            "query": query,
            "results": formatted
        })

    except Exception as e:
        return jsonify({"error": f"Chat engine failed: {e}"}), 500


# --------------------------------------------------------------------
# DEBUG ROUTE
# --------------------------------------------------------------------
@app.route("/debug")
def debug_route():
    """For quick Render verification — lists routes."""
    return jsonify({
        "routes": [str(r) for r in app.url_map.iter_rules()],
        "uploads": os.listdir(UPLOAD_DIR)
    })


# --------------------------------------------------------------------
# MAIN ENTRY
# --------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
