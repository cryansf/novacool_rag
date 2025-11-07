import os
import json
import threading
import time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from openai import OpenAI
from bs4 import BeautifulSoup
import requests
from PyPDF2 import PdfReader
from docx import Document

# ✅ Confirm startup
print("✅ app_flask.py loaded successfully (background worker enabled)")

# --- Flask setup ---
app = Flask(__name__)
CORS(app)

# --- Directories ---
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
LOG_FILE = os.path.join(DATA_DIR, "progress.json")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# --- OpenAI client (legacy-compatible stable) ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Global state ---
status = {"running": False, "stage": "idle", "details": ""}


# ---------- Helpers ----------
def update_status(stage: str, details: str = ""):
    """Save current status to /data/progress.json and memory."""
    status["stage"] = stage
    status["details"] = details
    with open(LOG_FILE, "w") as f:
        json.dump(status, f, indent=2)
    print(f"[progress] {stage}: {details}")


def read_text_from_file(path):
    """Extract readable text from pdf/docx/txt/html."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".docx":
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)
        elif ext == ".html":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f, "html.parser")
                return soup.get_text(separator="\n")
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as e:
        return f"[error extracting text from {path}: {e}]"


def embed_text(content: str, chunk_size=5000):
    """Generate embeddings for text content in chunks."""
    text = content.strip()
    if not text:
        return []
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    embeddings = []
    for i, chunk in enumerate(chunks, 1):
        try:
            resp = client.embeddings.create(
                input=chunk,
                model="text-embedding-3-large"
            )
            embeddings.append(resp.data[0].embedding)
            update_status("embedding", f"Chunk {i}/{len(chunks)}")
            time.sleep(0.2)
        except Exception as e:
            update_status("error", f"Embedding failed on chunk {i}: {e}")
    return embeddings


def crawl_website(url, limit=10000):
    """Recursively crawl and collect plain text from a website."""
    visited = set()
    texts = []

    def crawl(u):
        if len(visited) >= limit:
            return
        try:
            r = requests.get(u, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            texts.append(soup.get_text(separator="\n"))
            visited.add(u)
            update_status("crawling", f"{len(visited)} pages visited")
            for link in soup.find_all("a", href=True):
                full = requests.compat.urljoin(u, link["href"])
                if full.startswith(url) and full not in visited:
                    crawl(full)
        except Exception as e:
            update_status("error", f"Failed to crawl {u}: {e}")

    crawl(url)
    return texts


# ---------- Background Workers ----------
def background_reindex():
    status["running"] = True
    update_status("reindexing", "Collecting uploaded files")
    files = [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)]
    for i, path in enumerate(files, 1):
        content = read_text_from_file(path)
        embed_text(content)
        update_status("reindexing", f"Processed {i}/{len(files)} files")
    status["running"] = False
    update_status("idle", "Reindex complete")


def background_crawl(url):
    status["running"] = True
    update_status("crawling", f"Starting crawl for {url}")
    texts = crawl_website(url)
    combined = "\n\n".join(texts)
    embed_text(combined)
    status["running"] = False
    update_status("idle", f"Crawl complete for {url}")


# ---------- Flask Routes ----------
@app.route("/")
def home():
    return jsonify({"message": "Server running ✅"})


@app.route("/status")
def get_status():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            data = json.load(f)
        return jsonify(data)
    return jsonify(status)


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(path)
    update_status("uploaded", f"File saved: {file.filename}")
    return jsonify({"message": "File uploaded successfully"})


@app.route("/reindex", methods=["POST"])
def reindex():
    if status["running"]:
        return jsonify({"error": "Reindex already running"}), 409
    threading.Thread(target=background_reindex, daemon=True).start()
    return jsonify({"message": "Reindexing started"})


@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.get_json(force=True)
    url = data.get("url")
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400
    if status["running"]:
        return jsonify({"error": "Another job is running"}), 409
    threading.Thread(target=background_crawl, args=(url,), daemon=True).start()
    return jsonify({"message": f"Crawl started for {url}"})


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        # simplified mock query response (no vector store yet)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Answer clearly and concisely."},
                {"role": "user", "content": query}
            ]
        )
        answer = response.choices[0].message.content
        return jsonify({"answer": answer})
    except Exception as e:
        update_status("error", f"Chat failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/uploader")
def uploader_page():
    return render_template("uploader.html")


# ---------- Main ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
