import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# === Local imports ===
from rag_pipeline import ingest_text, query_text  # your embedding and retrieval logic
from crawler_controller import crawl_and_ingest   # autonomous crawler function

# === Load environment variables ===
load_dotenv()

# === Initialize app ===
app = Flask(__name__)
CORS(app)

# === Health Check Route (root) ===
@app.route("/", methods=["GET"])
def home():
    """Basic health check endpoint for Render."""
    return jsonify({
        "status": "ok",
        "message": "Novacool RAG API is live!"
    }), 200


# === File Upload + Ingestion Route ===
@app.route("/upload", methods=["POST"])
def upload_files():
    """
    Uploads PDF/DOCX files, stores them in /uploads, and indexes into FAISS.
    """
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files in request."}), 400

        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "Empty upload request."}), 400

        os.makedirs("uploads", exist_ok=True)
        uploaded = []

        for f in files:
            save_path = os.path.join("uploads", f.filename)
            f.save(save_path)
            uploaded.append(save_path)

        # Call your ingestion pipeline
        for path in uploaded:
            ingest_text(path)

        return jsonify({
            "status": "success",
            "files": uploaded,
            "message": "Files uploaded and indexed successfully."
        }), 200

    except Exception as e:
        print("[Upload Error]", e)
        return jsonify({"error": str(e)}), 500


# === Chat / Query Route ===
@app.route("/chat", methods=["POST"])
def chat():
    """
    Handles user queries using FAISS + OpenAI semantic search pipeline.
    """
    try:
        data = request.get_json()
        query = data.get("query", "").strip()

        if not query:
            return jsonify({"error": "Query is empty."}), 400

        # Run the retrieval and answer generation
        answer = query_text(query)
        return jsonify({"answer": answer}), 200

    except Exception as e:
        print("[Chat Error]", e)
        return jsonify({"error": str(e)}), 500


# === Autonomous Web Crawl Route ===
@app.route("/crawl", methods=["POST"])
def crawl():
    """
    Triggers a background crawl and auto-ingestion of web pages.
    """
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "No URL provided."}), 400

        crawl_and_ingest(url)
        return jsonify({"status": "success", "url": url}), 200

    except Exception as e:
        print("[Crawl Error]", e)
        return jsonify({"error": str(e)}), 500


# === MAIN ENTRYPOINT ===
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
