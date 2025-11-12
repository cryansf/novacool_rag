import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# === Import your internal RAG modules ===
from rag_pipeline import ingest_text, query_text  # FAISS + Embeddings
from crawler_controller import crawl_and_ingest   # Web crawler
from ingest import ingest_files                   # File upload handler

# === Flask app setup ===
app = Flask(__name__)
CORS(app)

# === ROUTE: Homepage (Control Console UI) ===
@app.route("/")
def index():
    return render_template("index.html")

# === ROUTE: File Upload + Ingestion ===
@app.route("/upload", methods=["POST"])
def upload():
    """Handles file uploads and ingestion into FAISS index."""
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files in request."}), 400

        uploaded_files = request.files.getlist("files")
        if not uploaded_files:
            return jsonify({"error": "No files selected."}), 400

        saved_paths = []
        for f in uploaded_files:
            save_path = os.path.join("uploads", f.filename)
            f.save(save_path)
            saved_paths.append(save_path)

        # Ingest and embed the files
        stats = ingest_files(saved_paths)
        return jsonify({
            "message": "Files uploaded and ingested successfully.",
            "stats": stats
        }), 200

    except Exception as e:
        print("[Upload Error]", e)
        return jsonify({"error": str(e)}), 500

# === ROUTE: Web Crawler ===
@app.route("/crawl", methods=["POST"])
def crawl():
    """Triggers autonomous crawling + ingestion."""
    try:
        data = request.get_json()
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"error": "Missing URL"}), 400

        result = crawl_and_ingest(url)
        return jsonify({"message": "Crawl complete", "result": result}), 200

    except Exception as e:
        print("[Crawler Error]", e)
        return jsonify({"error": str(e)}), 500

# === ROUTE: Chat / Semantic Query ===
@app.route("/chat", methods=["POST"])
def chat():
    """Handles semantic search / question answering queries."""
    data = request.get_json()

    # --- Validate input ---
    if not data or "query" not in data:
        return jsonify({"error": "Missing query field."}), 400

    query = data["query"].strip()
    if not query:
        return jsonify({"error": "Query is empty."}), 400

    # --- Run the query ---
    try:
        # Use your RAG pipeline to get an answer from FAISS + embeddings
        answer = query_text(query)

        # Send a clean JSON response back to the front-end
        return jsonify({"response": answer}), 200

    # --- Handle errors cleanly ---
    except Exception as e:
        print("[Chat Error]", e)
        return jsonify({"error": str(e)}), 500


# === MAIN ENTRYPOINT ===
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
