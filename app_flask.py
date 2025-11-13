import os
import json
import uuid
import shutil
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# --- Embeddings & FAISS ---
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# --- Text extraction ---
import html2text
from bs4 import BeautifulSoup

# --- Vector Model ---
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# ============================================================
# 🔥 FLASK INIT
# ============================================================
app = Flask(__name__)

CORS(app)

UPLOAD_DIR = "data/uploads"
CRAWL_DIR = "data/crawled"
DB_DIR = "data/index"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CRAWL_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = f"{DB_DIR}/vectors.faiss"
META_PATH = f"{DB_DIR}/meta.json"

# ============================================================
# 🔥 VECTOR DB HELPERS
# ============================================================

def load_db():
    if os.path.exists(DB_PATH):
        index = faiss.read_index(DB_PATH)
    else:
        index = faiss.IndexFlatL2(384)
    
    if os.path.exists(META_PATH):
        with open(META_PATH, "r") as f:
            meta = json.load(f)
    else:
        meta = []
    return index, meta


def save_db(index, meta):
    faiss.write_index(index, DB_PATH)
    with open(META_PATH, "w") as f:
        json.dump(meta, f)


def embed_text(text):
    vec = embedder.encode([text])[0]
    return vec.astype("float32")


# ============================================================
# 🔥 INGEST TEXT → VECTOR STORE
# ============================================================

def ingest_text(text, source):
    if not text.strip():
        return False

    vec = embed_text(text)
    index, meta = load_db()

    index.add(np.array([vec]))
    meta.append({"source": source, "text": text[:500]})

    save_db(index, meta)
    return True


# ============================================================
# 🔥 EXTRACT TEXT FROM HTML
# ============================================================

def extract_from_html(content):
    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text(" ", strip=True)
    return text


# ============================================================
# 🔥 WEBSITE CRAWLER
# ============================================================

def crawl_url(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        text = extract_from_html(r.text)
        return text
    except Exception as e:
        print("Crawl error:", e)
        return ""


# ============================================================
# 🔥 ROUTE: CHAT
# ============================================================

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    query = data.get("message", "")

    if not query:
        return jsonify({"response": "No query provided"})

    index, meta = load_db()

    if index.ntotal == 0:
        return jsonify({"response": "Knowledge base is empty."})

    qvec = embed_text(query)
    D, I = index.search(np.array([qvec]), 5)

    matches = [meta[i]["text"] for i in I[0] if i < len(meta)]

    context = "\n".join(matches)

    # --- Call OpenAI ---
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")

    completion = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are Novacool UEF's expert AI assistant."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{query}"}
        ]
    )

    answer = completion.choices[0].message.content
    return jsonify({"response": answer})


# ============================================================
# 🔥 ROUTE: ASK (alias)
# ============================================================

@app.route("/ask", methods=["POST"])
def ask():
    return chat()


# ============================================================
# 🔥 ROUTE: UPLOAD FOR INGESTION
# ============================================================

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"})

    file = request.files["file"]
    fname = secure_filename(file.filename)
    path = os.path.join(UPLOAD_DIR, fname)
    file.save(path)

    # Extract text (simple UTF-8 decode)
    try:
        content = file.read().decode("utf-8", errors="ignore")
    except:
        content = ""

    if not content.strip():
        return jsonify({"error": "No text could be extracted from this file"})

    ingest_text(content, fname)
    return jsonify({"status": "ok", "file": fname})


# ============================================================
# 🔥 ROUTE: REINDEX (full rebuild)
# ============================================================

@app.route("/reindex", methods=["POST"])
def reindex():
    # Clear previous DB
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    if os.path.exists(META_PATH): os.remove(META_PATH)

    for fname in os.listdir(UPLOAD_DIR):
        fpath = os.path.join(UPLOAD_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
                ingest_text(text, fname)
        except:
            continue

    return jsonify({"status": "reindexed"})


# ============================================================
# 🔥 ROUTE: WEBSITE CRAWLER INGEST
# ============================================================

@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.json
    url = data.get("url", "")

    if not url.startswith("http"):
        return jsonify({"error": "Invalid URL"})

    text = crawl_url(url)
    if not text.strip():
        return jsonify({"error": "Could not extract text"})

    ingest_text(text, url)
    return jsonify({"status": "indexed", "url": url})


# ============================================================
# 🔥 ROUTE: ADMIN UPLOADER DASHBOARD
# ============================================================

@app.route("/admin/uploader")
def admin_uploader():
    return send_from_directory("static", "uploader.html")


# ============================================================
# 🔥 STATIC SERVE (widget, loader, logos)
# ============================================================

@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)


# ============================================================
# 🔥 REQUIRED HEADERS FOR GETRESPONSE WIDGET
# ============================================================

@app.after_request
def add_headers(response):
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["Content-Security-Policy"] = "frame-ancestors *"
    return response


# ============================================================
# 🔥 HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ============================================================
# 🔥 RUN APP (Render uses Gunicorn, not this block)
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
