from flask import Flask, render_template, request, jsonify
import os
import openai
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load your OpenAI key from environment variable (Render → Environment)
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return "<h2>Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

# -------------------------- FILE UPLOADER -----------------------------------

@app.route("/uploader")
def uploader_page():
    return render_template("uploader.html")

@app.route("/upload", methods=["POST"])
def upload_files():
    """
    Handles multiple file uploads and indexes PDFs (placeholder).
    Replace indexing section with your actual RAG embedding logic.
    """
    if "files" not in request.files:
        return jsonify({"status": "No files found in request"}), 400

    files = request.files.getlist("files")
    saved_files = []

    for file in files:
        if not file.filename:
            continue

        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        saved_files.append(save_path)

        # Example indexing placeholder
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(save_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            print(f"Indexed PDF: {filename} ({len(text)} chars)")
        else:
            print(f"Saved file {filename}")

    return jsonify({"status": f"{len(saved_files)} file(s) uploaded and indexed successfully."})

# -------------------------- REINDEX -----------------------------------------

@app.route("/reindex", methods=["POST"])
def reindex_all():
    """
    Clears and rebuilds your RAG index from uploaded files (placeholder).
    """
    try:
        indexed_count = 0
        for filename in os.listdir(UPLOAD_FOLDER):
            if not filename.lower().endswith(".pdf"):
                continue
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            indexed_count += 1
            print(f"Reindexed {filename} ({len(text)} chars)")

        return jsonify({"status": f"Reindexed {indexed_count} document(s) successfully."})
    except Exception as e:
        print("Reindex error:", e)
        return jsonify({"status": f"Reindex failed: {e}"}), 500

# -------------------------- WEB CRAWLER -------------------------------------

@app.route("/crawl", methods=["POST"])
def crawl_site():
    """
    Crawls a single webpage and (optionally) indexes its text.
    """
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"status": "No URL provided"}), 400

        print(f"Starting crawl for: {url}")
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return jsonify({"status": f"Failed to fetch {url} (HTTP {resp.status_code})"}), 400

        text = resp.text[:2000]
        print(f"Crawled {len(resp.text)} characters from {url}")
        return jsonify({"status": f"Crawled {url} successfully ({len(resp.text)} chars)."})
    except Exception as e:
        print("Crawl error:", e)
        return jsonify({"status": f"Crawl failed: {e}"}), 500

# ----------------------------- CHAT UI --------------------------------------

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/widget")
def widget_page():
    return render_template("widget.html")

# Optional alias for admin-style URLs
@app.route("/admin/uploader")
def admin_uploader_alias():
    return render_template("uploader.html")

# ----------------------------- CHAT API -------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat_api():
    """
    Primary chat endpoint for /chat and /widget.
    """
    try:
        data = request.get_json(force=True)
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        # Call OpenAI model (or your own RAG retrieval chain)
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Novacool’s RAG assistant. Be factual and concise."},
                {"role": "user", "content": user_message}
            ]
        )

        reply = response.choices[0].message["content"].strip()
        return jsonify({"reply": reply})

    except Exception as e:
        print("Chat API error:", e)
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
