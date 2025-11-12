import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from rag_pipeline import ingest_text, query_text
from crawler_controller import crawl_and_ingest  # ✅ Correct import
from werkzeug.utils import secure_filename

# --- Initialize Flask app ---
app = Flask(__name__)
CORS(app)

# --- Paths ---
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# === ROUTES ===

@app.route("/")
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "Novacool RAG API is live!"
    })


@app.route("/chat", methods=["POST"])
def chat():
    """Handles semantic search / question answering queries."""
    try:
        data = request.get_json()
        query = data.get("query", "").strip()

        if not query:
            return jsonify({"error": "Query is empty."}), 400

        # Run semantic query against FAISS / embeddings
        answer = query_text(query)
        return jsonify({"answer": answer})

    except Exception as e:
        print("[Chat Error]", e)
        return jsonify({"error": str(e)}), 500


@app.route("/upload", methods=["POST"])
def upload():
    """Handles PDF/DOCX uploads and ingestion into FAISS."""
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files in request."}), 400

        uploaded_files = request.files.getlist("files")
        saved = []

        for file in uploaded_files:
            filename = secure_filename(file.filename)
            if not filename:
                continue
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            saved.append(file_path)

        if not saved:
            return jsonify({"error": "No valid files uploaded."}), 400

        # Ingest uploaded files into FAISS
        stats = ingest_text(saved)
        return jsonify({
            "message": f"{len(saved)} file(s) uploaded and indexed successfully.",
            "details": stats
        })

    except Exception as e:
        print("[Upload Error]", e)
        return jsonify({"error": str(e)}), 500


@app.route("/crawl", methods=["POST"])
def crawl():
    """Autonomous web crawler trigger"""
    try:
        data = request.get_json()
        url = data.get("url")
        if not url:
            return jsonify({"error": "Missing URL"}), 400

        crawl_and_ingest(url)
        return jsonify({"message": f"Crawling complete for {url}."})

    except Exception as e:
        print("[Crawler Error]", e)
        return jsonify({"error": str(e)}), 500


# === MAIN ENTRYPOINT ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
