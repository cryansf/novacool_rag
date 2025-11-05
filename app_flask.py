# app_flask.py — Novacool's Assistant (Flask on Render)
# - Full-page chat UI (/widget)
# - Admin uploader (/admin/uploader)
# - Crawl button with progress bar + live logs (/crawl)
# - Vector store: ./data/vecs.npy + ./data/meta.jsonl

import os, io, re, json, time, uuid, pathlib, urllib.parse
from typing import List, Dict, Any
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
import requests
import numpy as np
from bs4 import BeautifulSoup

# ---------- Config ----------
APP_TITLE = "Novacool’s Assistant"
DATA_DIR = "data"
UPLOAD_DIR = f"{DATA_DIR}/uploads"
META_PATH = f"{DATA_DIR}/meta.jsonl"
VEC_PATH  = f"{DATA_DIR}/vecs.npy"

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL  = "gpt-4o-mini"
TOP_K = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

USER_AGENT = "Novacool-RAG/1.0"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder=None)

# ---------- Utils ----------
def normspace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> List[str]:
    t = normspace(text)
    if not t: return []
    out, start, L = [], 0, len(t)
    while start < L:
        end = min(L, start + size)
        out.append(t[start:end])
        if end == L: break
        start = max(0, end - overlap)
    return out

def load_meta() -> List[Dict[str, Any]]:
    if not os.path.exists(META_PATH): return []
    with open(META_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def save_meta(metas: List[Dict[str, Any]]):
    with open(META_PATH, "w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

def load_vecs() -> np.ndarray:
    if not os.path.exists(VEC_PATH):
        return np.zeros((0, 1536), dtype=np.float32)
    return np.load(VEC_PATH)

def save_vecs(arr: np.ndarray):
    np.save(VEC_PATH, arr)

def openai_embeddings(texts: List[str]) -> np.ndarray:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key: raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json={"input": texts, "model": EMBED_MODEL}, timeout=60)
    r.raise_for_status()
    arr = np.array([d["embedding"] for d in r.json()["data"]], dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return (arr / norms).astype(np.float32)

def add_chunks(chunks: List[Dict[str, Any]]) -> int:
    if not chunks: return 0
    texts = [c["text"] for c in chunks]
    vecs_new = openai_embeddings(texts)
    vecs_old = load_vecs()
    vecs = vecs_new if vecs_old.shape[0] == 0 else np.vstack([vecs_old, vecs_new])
    save_vecs(vecs)
    metas = load_meta()
    for c in chunks:
        c["id"] = str(uuid.uuid4())
    metas.extend(chunks)
    save_meta(metas)
    return len(chunks)

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def health():
    return Response("OK", mimetype="text/plain")

@app.route("/widget", methods=["GET"])
def widget():
    return render_template("widget.html", title=APP_TITLE)

@app.route("/admin/uploader", methods=["GET"])
def uploader():
    return render_template("uploader.html", title="Uploader | Novacool")

@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"error": "no files"}), 400
    saved = []
    for f in request.files.getlist("files"):
        filename = pathlib.Path(f.filename).name
        if not filename: continue
        dest = os.path.join(UPLOAD_DIR, filename)
        f.save(dest)
        saved.append(filename)
    return jsonify({"saved": saved})

@app.route("/reindex", methods=["POST"])
def reindex():
    added_total, chunks = 0, []
    for root, _, files in os.walk(UPLOAD_DIR):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                with open(path, "rb") as f: b = f.read()
                body = ""
                if path.lower().endswith(".pdf"):
                    from pypdf import PdfReader
                    r = PdfReader(io.BytesIO(b))
                    body = "\n".join([normspace(p.extract_text() or "") for p in r.pages])
                elif path.lower().endswith(".docx"):
                    import docx
                    d = docx.Document(io.BytesIO(b))
                    body = "\n".join([normspace(p.text) for p in d.paragraphs])
                else:
                    try: body = b.decode("utf-8")
                    except: body = b.decode("latin-1", errors="ignore")
                for c in chunk_text(body):
                    chunks.append({"source_type": "file","source": f"/uploads/{fn}","location": "N/A","text": c})
            except Exception:
                continue
    added_total += add_chunks(chunks)
    return jsonify({"reindexed_chunks": added_total})

# ---------- Crawl with progress ----------
@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url: return jsonify({"error": "No URL provided"}), 400
    if not re.match(r"^https?://", url): url = "https://" + url

    steps = []
    def log(msg): steps.append(msg)

    try:
        log(f"Fetching {url} ...")
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20, allow_redirects=True)
        log(f"Status {r.status_code}, Content-Type {r.headers.get('Content-Type','?')}")
    except Exception as e:
        return jsonify({"error": f"Fetch failed: {e}", "log": steps}), 400

    if r.status_code != 200:
        return jsonify({"error": f"Bad HTTP status {r.status_code}", "log": steps}), 400

    if "text/html" not in r.headers.get("Content-Type", "").lower():
        return jsonify({"error": f"Unexpected content type: {r.headers.get('Content-Type','?')}", "log": steps}), 400

    log("Parsing HTML...")
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]): tag.extract()
    text = normspace(soup.get_text(separator="\n"))
    log(f"Extracted {len(text)} characters of text")

    if not text or len(text) < 100:
        return jsonify({"error": "No usable text found", "log": steps}), 400

    log("Chunking text...")
    chunks = [{
        "source_type": "html",
        "source": url,
        "location": "webpage",
        "text": c
    } for c in chunk_text(text)]

    log(f"Embedding {len(chunks)} chunks...")
    added = add_chunks(chunks)
    log(f"✅ Done! Added {added} chunks from {url}")

    return jsonify({"message": f"Embedded {added} chunks from {url}", "added": added, "log": steps})

@app.route("/uploads/<path:filename>")
def uploads_public(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
