# app_flask.py — Novacool's Assistant (Flask on Render)
# - Full-page chat UI (/widget)
# - Drag & drop uploader (/admin/uploader) -> POST /upload
# - Workflow dashboard (/admin/status)
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

HOST_WHITELIST = [d.strip().lower() for d in os.getenv("HOST_DOMAIN_WHITELIST","novacool.com").split(",") if d.strip()]
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
    if not os.path.exists(VEC_PATH): return np.zeros((0, 1536), dtype=np.float32)
    return np.load(VEC_PATH)

def save_vecs(arr: np.ndarray):
    np.save(VEC_PATH, arr)

def openai_embeddings(texts: List[str]) -> np.ndarray:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
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
    for c in chunks: c["id"] = str(uuid.uuid4())
    metas.extend(chunks)
    save_meta(metas)
    return len(chunks)

def search(query: str, k: int = TOP_K) -> List[Dict[str, Any]]:
    vecs = load_vecs()
    metas = load_meta()
    if vecs.shape[0] == 0: return []
    qv = openai_embeddings([query])[0:1]
    sims = (vecs @ qv.T).reshape(-1)
    idx = np.argsort(-sims)[:min(k, vecs.shape[0])]
    out = []
    for i in idx:
        m = metas[i].copy()
        m["_score"] = float(sims[i])
        out.append(m)
    return out

def call_llm(question: str, ctx_blocks: List[str], cites: List[str]) -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        stitched = "\n\n".join(f"- {c[:500]}..." for c in ctx_blocks)
        return f"(No OpenAI key configured)\n\n{stitched}\n\nSources: " + "; ".join(cites)
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    prompt = (
        "You are Novacool’s Assistant. Answer ONLY from the provided context. "
        "If it isn't in the context, say you don't know. Be concise and end with a 'Sources:' list.\n\n"
        f"Question: {question}\n\nContext:\n" + "\n\n".join(ctx_blocks) + "\n\nAnswer:"
    )
    data = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "Precise, cite sources, no hallucinations."},
            {"role": "user",    "content": prompt}
        ],
        "temperature": 0.2
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    ans = r.json()["choices"][0]["message"]["content"].strip()
    if "Sources:" not in ans:
        ans += "\n\nSources: " + "; ".join(cites)
    return ans

def ext(path: str) -> str:
    return pathlib.Path(path).suffix.lower()

def parse_pdf(bytes_blob: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""
    r = PdfReader(io.BytesIO(bytes_blob))
    out = []
    for p in r.pages:
        try: out.append(normspace(p.extract_text() or ""))
        except Exception: out.append("")
    return "\n".join(out)

def parse_docx(bytes_blob: bytes) -> str:
    try:
        import docx as _docx
    except Exception:
        return ""
    d = _docx.Document(io.BytesIO(bytes_blob))
    return "\n".join([normspace(p.text) for p in d.paragraphs if normspace(p.text)])

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def health(): return Response("OK", mimetype="text/plain")

@app.route("/widget", methods=["GET"])
def widget(): return render_template("widget.html", title=APP_TITLE)

@app.route("/admin/uploader", methods=["GET"])
def uploader(): return render_template("uploader.html", title="Uploader | Novacool")

@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files: return jsonify({"error": "no files"}), 400
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
    added_total = 0
    chunks = []
    for root, _, files in os.walk(UPLOAD_DIR):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                with open(path, "rb") as f: b = f.read()
                body = ""
                if ext(path) == ".pdf": body = parse_pdf(b)
                elif ext(path) == ".docx": body = parse_docx(b)
                else:
                    try: body = b.decode("utf-8")
                    except Exception: body = b.decode("latin-1", errors="ignore")
                for c in chunk_text(body):
                    chunks.append({
                        "source_type": ext(path).lstrip(".") or "text",
                        "source": f"/uploads/{fn}",
                        "location": "N/A",
                        "text": c
                    })
            except Exception:
                continue
    added_total += add_chunks(chunks)
    return jsonify({"reindexed_chunks": added_total})

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True, silent=True) or {}
    q = (data.get("question") or "").strip()
    if not q:
        return jsonify({"error": "empty question"}), 400
    ctx = search(q, k=TOP_K)
    if not ctx:
        answer = "I don’t have any indexed documents yet. Please upload files and click Reindex."
        return jsonify({"answer": answer, "citations": []})
    blocks, cites = [], []
    for i, c in enumerate(ctx, 1):
        src = f"{c['source']}" if c.get("location") in (None, "", "N/A") else f"{c['source']} ({c['location']})"
        blocks.append(f"[{i}] Source: {src}\n{c['text']}")
        cites.append(f"[{i}] {src}")
    answer = call_llm(q, blocks, cites)
    return jsonify({
        "answer": answer,
        "citations": [{"source": c["source"], "location": c.get("location", "N/A"), "score": c["_score"]} for c in ctx]
    })

@app.route("/uploads/<path:filename>")
def uploads_public(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---------- Admin Workflow Dashboard ----------
@app.route("/admin/status", methods=["GET"])
def admin_status():
    """Visual workflow dashboard: show uploads, chunk count, and reindex button."""
    try:
        files = sorted(os.listdir(UPLOAD_DIR))
    except FileNotFoundError:
        files = []
    meta_count = 0
    if os.path.exists(META_PATH):
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta_count = sum(1 for _ in f)
    html = [
        "<html><head><title>Novacool RAG Status</title></head><body style='font-family:system-ui;background:#0b0b0d;color:#eee;padding:20px;'>",
        "<h1>📊 Novacool RAG Status</h1>",
        f"<p><b>Uploaded files:</b> {len(files)} total</p>",
        "<ul>"
    ]
    for f in files:
        html.append(f"<li><a href='/uploads/{f}' style='color:#9cf'>{f}</a></li>")
    html.append("</ul>")
    html.append(f"<p><b>Embedded chunks:</b> {meta_count}</p>")
    html.append("""
        <form action="/reindex" method="post">
            <button style="background:#e11d2e;border:none;color:white;padding:10px 14px;border-radius:8px;font-weight:600;cursor:pointer;">🔄 Reindex Now</button>
        </form>
    """)
    html.append("<p style='margin-top:20px'><a href='/admin/uploader' style='color:#ff445a'>⬆️ Back to uploader</a></p>")
    html.append("</body></html>")
    return "\n".join(html)

# -------------- Run local (Render uses gunicorn) --------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
