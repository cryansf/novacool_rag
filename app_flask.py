import os
import time
import json
import traceback
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
from openai.error import RateLimitError, ServiceUnavailableError, APIError

# --------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = "text-embedding-3-small"

UPLOAD_DIR = "/data/uploads"
PROGRESS_FILE = "/data/index_progress.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------------------------------------------------
# UTILITY FUNCTIONS
# --------------------------------------------------------------------

def log_event(event):
    print(f"[{time.strftime('%H:%M:%S')}] {event}", flush=True)

def embed_text_with_retry(text, retries=5, delay=5):
    """Embed text with exponential backoff."""
    for attempt in range(retries):
        try:
            result = openai.embeddings.create(model=EMBED_MODEL, input=text)
            return result.data[0].embedding
        except (RateLimitError, ServiceUnavailableError, APIError) as e:
            log_event(f"⚠️ Retry {attempt+1}/{retries} after API error: {str(e)}")
            time.sleep(delay * (2 ** attempt))
        except Exception as e:
            log_event(f"❌ Unhandled embedding error: {e}")
            traceback.print_exc()
            break
    return None

def load_progress():
    """Load existing progress file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            log_event("⚠️ Failed to read progress file, starting fresh.")
    return {}

def save_progress(data):
    """Save progress to JSON file."""
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log_event(f"⚠️ Failed to save progress: {e}")

# --------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin/uploader")
def uploader():
    return render_template("uploader.html")

@app.route("/upload", methods=["POST"])
def upload_files():
    uploaded_files = request.files.getlist("file")
    file_names = []
    for file in uploaded_files:
        if file.filename:
            save_path = os.path.join(UPLOAD_DIR, file.filename)
            file.save(save_path)
            file_names.append(file.filename)
            log_event(f"✅ Uploaded: {file.filename}")
    return jsonify({"uploaded": file_names})

@app.route("/reindex", methods=["POST"])
def reindex_all():
    """Reindex all uploaded files with resume support."""
    progress = load_progress()
    completed_files = progress.get("completed", [])

    try:
        all_files = [f for f in os.listdir(UPLOAD_DIR)
                     if os.path.isfile(os.path.join(UPLOAD_DIR, f))]

        if not all_files:
            return jsonify({"error": "No files to reindex."}), 400

        pending_files = [f for f in all_files if f not in completed_files]
        log_event(f"🌀 Resuming reindex: {len(pending_files)} remaining of {len(all_files)} total")

        for i, file_name in enumerate(pending_files, start=1):
            file_path = os.path.join(UPLOAD_DIR, file_name)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            embedding = embed_text_with_retry(text)
            if embedding:
                completed_files.append(file_name)
                progress["completed"] = completed_files
                save_progress(progress)
                log_event(f"🧠 Indexed ({i}/{len(pending_files)}): {file_name}")
            else:
                log_event(f"❌ Failed to embed: {file_name}")

        log_event(f"✅ Reindex complete: {len(completed_files)}/{len(all_files)} files")
        return jsonify({"message": f"Reindex complete: {len(completed_files)}/{len(all_files)} files embedded."})

    except Exception as e:
        log_event(f"❌ Reindexing failed: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/crawl", methods=["POST"])
def crawl_site():
    try:
        log_event("🌐 Starting crawl...")
        # integrate crawl logic here
        return jsonify({"message": "Crawl started"})
    except Exception as e:
        log_event(f"❌ Crawl error: {e}")
        return jsonify({"error": str(e)}), 500

# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
