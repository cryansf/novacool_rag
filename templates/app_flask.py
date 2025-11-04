# app_flask.py — Novacool’s Assistant (Flask on Render)
# - Full-page chat UI (/widget)
# - Drag & drop uploader (/admin/uploader) -> POST /upload
# - Reindex button (/reindex) to (re)embed files in /data/uploads
# - Ask endpoint (/ask) using OpenAI (no openai package required)
# - Vector store: ./data/vecs.npy + ./data/meta.jsonl

import os, io, re, json, time, uuid, pathlib, urllib.parse, queue
from typing import List, Dict, Any, Optional
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

EMBED_MODEL = "text-embedding-3-small"   # 1536 dims
CHAT_MODEL  = "gpt-4o-mini"
TOP_K = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# allow crawling same-domain later (not used by default in this file)
HOST_WHITELIST = [d.strip().lower() for d in os.getenv("HOST_DOMAIN_WHITELIST","novacool.com").split(",") if d.strip()]
USER_AGENT = "Novacool-RAG/1.0"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder=None)

# ---------- Utils ----------
def normspace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    t = normspace(text)
    if not t:
        return []
    out, start, L = [], 0, len(t)
    while start < L:
        end = min(L, start + size)
        out.append(t[start:end])
        if end == L:
            break
        start = max(0, end - overlap)
    return out

def load_meta() -> List[Dict[str, Any]]:
    if not os.path.exists(META_PATH):
        return []
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

# ---------- Embeddings & LLM ----------
def openai_embeddings(texts: List[str]) -> np.ndarray:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    r = requests.post(url, headers=headers, json={"input": texts, "model": EMBED_MODEL}, timeout=60)
    r.raise_for_status()
    arr = np.array([d["embedding"] for d in r.json()["data"]], dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return (arr / norms).astype(np.float32)

def call_llm(question: str, ctx_blocks: List[str], cites: List[str]) -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        stitched = "\n\n".join(f"- {c[:500]}..." for c in ctx_blocks)
        return f"(No LLM key set)\n\n{stitched}\n\nSources: " + "; ".join(cites)
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    prompt = (
        "Answer ONLY from the provided context. If it's not there, say you don't know. "
        "Be concise and include a final 'Sources:' list.\n\n"
        f"Question: {question}\n\nContext:\n" + "\n\n".join(ctx_blocks) + "\n\nAnswer:"
    )
    data = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "Precise, cite sources, no hallucinations."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    r = requests.post(url, headers=headers, json=data, timeout=90)
    r.raise_for_status()
    ans = r.json()["choices"][0]["message"]["content"].strip()
    if "Sources:" not in ans:
        ans += "\n\nSources: " + "; ".join(cites)
    return ans

# ---------- Indexing ----------
def add_chunks(chunks: List[Dict[str, Any]]) -> int:
    if not chunks:
        return 0
    texts = [c["text"] for c in chunks if c.get("text")]
    if not texts:
        return 0
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

def ingest_file_bytes(filename: str, blob: bytes) -> List[Dict[str, Any]]:
    ext = pathlib.Path(filename).suffix.lower()
    chunks: List[Dict[str, Any]] = []
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(blob))
            for i, p in enumerate(r.pages):
                try:
                    txt = normspace(p.extract_text() or "")
                except Exception:
                    txt = ""
                for c in chunk_text(txt):
                    chunks.append({"source_type": "pdf", "source": filename, "location": f"p. {i+1}", "text": c})
        elif ext == ".docx":
            import docx as _docx
            d = _docx.Document(io.BytesIO(blob))
            body = "\n".join([normspace(p.text) for p in d.paragraphs if normspace(p.text)])
            for c in chunk_text(body):
                chunks.append({"source_type": "docx", "source": filename, "location": "N/A", "text": c})
        else:
            try:
                body = blob.decode("utf-8")
            except Exception:
                body = blob.decode("latin-1", errors="ignore")
            for c in chunk_text(body):
                chunks.append({"source_type": "text", "source": filename, "location": "N/A", "text": c})
    except Exception as e:
        raise RuntimeError(f"Failed to parse {filename}: {e}")
    return chunks

# ---------- Search ----------
def search(query: str, k: int = TOP_K) -> List[Dict[str, Any]]:
    vecs = load_vecs()
    metas = load_meta()
    if vecs.shape[0] == 0:
        return []
    qv = openai_embeddings([query])[0:1]
    sims = (vecs @ qv.T).reshape(-1)
    idx = np.argsort(-sims)[:min(k, vecs.shape[0])]
    out = []
    for i in idx:
        m = metas[i].copy()
        m["_score"] = float(sims[i])
        out.append(m)
    return out

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def health() -> Response:
    return Response("OK", mimetype="text/plain")

@app.route("/widget", methods=["GET"])
def widget() -> Response:
    # requires templates/widget.html
    return render_template("widget.html", title=APP_TITLE)

@app.route("/admin/uploader", methods=["GET"])
def uploader_page() -> Response:
    # requires templates/uploader.html
    return render_template("uploader.html", title=APP_TITLE)

@app.route("/upload", methods=["POST"])
def upload_files():
    if "files" not in request.files:
        return jsonify({"error": "no files"}), 400

    saved = []
    all_chunks: List[Dict[str, Any]] = []
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        filename = pathlib.Path(f.filename).name
        dest = os.path.join(UPLOAD_DIR, filename)
        blob = f.read()
        # save original
        with open(dest, "wb") as out:
            out.write(blob)
        saved.append(filename)
        # produce chunks
        all_chunks.extend(ingest_file_bytes(filename, blob))

    added = add_chunks(all_chunks)
    return jsonify({"saved": saved, "added_chunks": added})

@app.route("/reindex", methods=["POST"])
def reindex():
    """
    Re-reads every file under UPLOAD_DIR and rebuilds the vector store by appending
    new chunks. (It does not dedupe; for a fresh index, delete data/vecs.npy and data/meta.jsonl)
    """
    files = []
    for root, _, fnames in os.walk(UPLOAD_DIR):
        for fn in fnames:
            p = os.path.join(root, fn)
            files.append(p)

    if not files:
        return jsonify({"reindexed": 0, "files": []})

    all_chunks: List[Dict[str, Any]] = []
    for p in files:
        try:
            with open(p, "rb") as fh:
                blob = fh.read()
            relname = os.path.relpath(p, UPLOAD_DIR)
            all_chunks.extend(ingest_file_bytes(relname, blob))
        except Exception as e:
            return jsonify({"error": f"Failed {p}: {e}"}), 500

    added = add_chunks(all_chunks)
    return jsonify({"reindexed": added, "files": [os.path.relpath(p, UPLOAD_DIR) for p in files]})

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True, silent=True) or {}
    q = (data.get("question") or "").strip()
    if not q:
        return jsonify({"error": "empty question"}), 400

    ctx = search(q, k=TOP_K)
    blocks, cites = [], []
    for i, c in enumerate(ctx, 1):
        src = f"{c['source']} ({c['location']})" if c.get("location") and c["location"] != "N/A" else c.get("source", "N/A")
        blocks.append(f"[{i}] Source: {src}\n{c.get('text','')}")
        cites.append(f"[{i}] {src}")
    answer = call_llm(q, blocks, cites)
    return jsonify({
        "answer": answer,
        "citations": [
            {"source": c.get("source", "N/A"), "location": c.get("location", "N/A"), "score": c.get("_score", 0.0)}
            for c in ctx
        ]
    })

# (Optional) Serve uploaded originals for quick checks
@app.route("/uploads/<path:fname>")
def downloads(fname: str):
    return send_from_directory(UPLOAD_DIR, fname, as_attachment=False)

# ---------- Run (local) ----------
if __name__ == "__main__":
    # Helpful when testing locally (Render uses gunicorn start command)
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
