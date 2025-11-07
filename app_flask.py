import os, re, json, time, math, threading, requests
import numpy as np
from flask import Flask, request, jsonify, render_template, send_from_directory
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader

# ---------------- Config ----------------
DATA_DIR = "/data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
META_FILE = os.path.join(DATA_DIR, "meta.json")
VECS_FILE = os.path.join(DATA_DIR, "vecs.npy")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")

TOP_K = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-large"   # highest quality

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates")

# ---------------- Utilities ----------------
def normspace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    t = normspace(text)
    if not t: 
        return []
    out, start, L = [], 0, len(t)
    while start < L:
        end = min(L, start + size)
        out.append(t[start:end])
        if end == L:
            break
        start = end - overlap
    return out

def load_meta():
    try:
        with open(META_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except Exception:
        return []

def save_meta(meta):
    with open(META_FILE, "w", encoding="utf8") as f:
        json.dump(meta, f)

def load_vecs():
    if os.path.exists(VECS_FILE):
        return np.load(VECS_FILE)
    # 3072 dims for text-embedding-3-large
    return np.zeros((0, 3072), dtype=np.float32)

def save_vecs(arr):
    np.save(VECS_FILE, np.asarray(arr, dtype=np.float32))

def save_progress(d):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf8") as f:
            json.dump(d, f)
    except Exception:
        pass

def load_progress():
    try:
        with open(PROGRESS_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except Exception:
        return {"task": None, "state": "idle", "message": "", "processed": 0, "total": 0}

# ---------- OpenAI embeddings with retries ----------
def _sleep_backoff(try_idx, retry_after=None):
    # Honor Retry-After when present
    if retry_after:
        try:
            wait = float(retry_after)
            time.sleep(min(wait, 20.0))
            return
        except Exception:
            pass
    # exponential with small jitter
    base = min(2 ** try_idx, 16)
    time.sleep(base + (0.25 * (try_idx + 1)))

def openai_embeddings(texts, max_retries=6):
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    for attempt in range(max_retries):
        try:
            r = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={"model": EMBED_MODEL, "input": texts},
                timeout=120,
            )
            if r.status_code in (429, 500, 502, 503, 504):
                retry_after = r.headers.get("Retry-After")
                print(f"⚠️ Embedding transient error {r.status_code}. Retrying...", flush=True)
                _sleep_backoff(attempt, retry_after)
                continue
            r.raise_for_status()
            data = r.json()
            return [x["embedding"] for x in data["data"]]
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error on embeddings (attempt {attempt+1}): {e}", flush=True)
            _sleep_backoff(attempt)
    raise RuntimeError("Embedding failed after retries")

# ---------------- Background worker ----------------
worker_lock = threading.Lock()
worker_thread = None

def start_worker(target, *args, **kwargs):
    global worker_thread
    with worker_lock:
        if worker_thread and worker_thread.is_alive():
            return False
        worker_thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        worker_thread.start()
        return True

def set_progress(state=None, message=None, processed=None, total=None, task=None):
    p = load_progress()
    if state is not None: p["state"] = state
    if message is not None: p["message"] = message
    if processed is not None: p["processed"] = processed
    if total is not None: p["total"] = total
    if task is not None: p["task"] = task
    p["ts"] = int(time.time())
    save_progress(p)

def reindex_worker_incremental():
    set_progress(task="reindex", state="running", message="Scanning uploads...", processed=0, total=0)
    try:
        existing_meta = load_meta()
        existing_vecs = load_vecs()
        indexed_files = {m.get("file"): m.get("mtime", 0) for m in existing_meta}
        new_texts, new_metas = [], []

        files = sorted(os.listdir(UPLOAD_DIR))
        for fn in files:
            fp = os.path.join(UPLOAD_DIR, fn)
            if not os.path.isfile(fp): 
                continue
            mtime = os.path.getmtime(fp)
            if fn in indexed_files and mtime <= indexed_files[fn]:
                print(f"⏩ Skipping unchanged file: {fn}", flush=True)
                continue

            print(f"📘 Processing new or updated file: {fn}", flush=True)
            if fn.lower().endswith(".txt"):
                text = open(fp, encoding="utf8", errors="ignore").read()
            elif fn.lower().endswith(".pdf"):
                text = " ".join(page.extract_text() or "" for page in PdfReader(fp).pages)
            elif fn.lower().endswith(".docx"):
                try:
                    doc = Document(fp)
                    text = " ".join(p.text for p in doc.paragraphs)
                except Exception as e:
                    print(f"⚠️ Skipping bad DOCX {fn}: {e}", flush=True)
                    continue
            else:
                print(f"⚠️ Unsupported file type skipped: {fn}", flush=True)
                continue

            for chunk in chunk_text(text):
                new_metas.append({"file": fn, "mtime": mtime, "text": chunk})
                new_texts.append(chunk)

        if not new_texts:
            set_progress(state="done", message="No new or modified files.", processed=0, total=0)
            return

        set_progress(message="Embedding chunks...", processed=0, total=len(new_texts))
        batch_size = 25
        new_vecs = []
        batches = math.ceil(len(new_texts) / batch_size)

        for i in range(0, len(new_texts), batch_size):
            batch = new_texts[i:i+batch_size]
            batch_num = i // batch_size + 1
            print(f"📦 Embedding batch {batch_num}/{batches} ({len(batch)} chunks)...", flush=True)
            # retry whole batch up to 5 times
            for retry in range(5):
                try:
                    vecs = openai_embeddings(batch)
                    new_vecs.extend(vecs)
                    processed = min(i + len(batch), len(new_texts))
                    set_progress(message=f"Completed batch {batch_num}/{batches}", processed=processed)
                    print(f"✅ Completed batch {batch_num}/{batches}", flush=True)
                    break
                except Exception as e:
                    print(f"❌ Error embedding batch {batch_num}, attempt {retry+1}: {type(e).__name__} – {e}", flush=True)
                    if retry < 4:
                        print("⏳ Waiting 10s before retry...", flush=True)
                        time.sleep(10)
                    else:
                        print("🚫 Skipping this batch after 5 failed attempts.", flush=True)
            time.sleep(2)

        # Merge & persist
        all_meta = existing_meta + new_metas
        if existing_vecs.size:
            all_vecs = np.vstack([existing_vecs, np.array(new_vecs, dtype=np.float32)])
        else:
            all_vecs = np.array(new_vecs, dtype=np.float32)

        save_meta(all_meta)
        save_vecs(all_vecs)
        set_progress(state="done", message=f"Incremental reindex complete: {len(new_vecs)} new chunks.", processed=len(new_texts), total=len(new_texts))
        print(f"🎉 Incremental reindex complete: {len(new_vecs)} new chunks.", flush=True)
    except Exception as e:
        set_progress(state="error", message=str(e))
        print(f"❌ Reindex worker error: {e}", flush=True)

def crawl_once(url: str):
    set_progress(task="crawl", state="running", message=f"Crawling {url}...", processed=0, total=0)
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","noscript"]):
            tag.decompose()
        text = normspace(soup.get_text())
        if len(text) > 10000:
            print(f"⚠️ Page too long ({len(text)} chars) – truncating to 10,000.", flush=True)
            text = text[:10000]
        chunks = chunk_text(text)
        if not chunks:
            set_progress(state="error", message="No text found on page.")
            return
        set_progress(message=f"Embedding {len(chunks)} chunks from crawl...", processed=0, total=len(chunks))
        # Single batch is fine here
        vecs = openai_embeddings(chunks)
        metas = [{"file": f"Crawl:{url}", "mtime": time.time(), "text": c} for c in chunks]
        old_m, old_v = load_meta(), load_vecs()
        save_meta(old_m + metas)
        if old_v.size:
            save_vecs(np.vstack([old_v, np.array(vecs, dtype=np.float32)]))
        else:
            save_vecs(np.array(vecs, dtype=np.float32))
        set_progress(state="done", message=f"Crawl complete: {len(chunks)} chunks.", processed=len(chunks), total=len(chunks))
        print(f"🎉 Crawl complete: {len(chunks)} chunks.", flush=True)
    except Exception as e:
        set_progress(state="error", message=f"Crawl error: {e}")
        print(f"❌ Crawl error: {e}", flush=True)

# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template("widget.html")

@app.route("/widget")
def widget():
    return render_template("widget.html")

@app.route("/admin/uploader")
def uploader_page():
    try:
        return render_template("uploader.html")
    except Exception:
        return "<h3>Uploader template missing. Place templates/uploader.html</h3>"

@app.route("/uploads/<path:filename>")
def get_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    saved = []
    for f in files:
        path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(path)
        saved.append(f.filename)
    print(f"📁 Uploaded files: {saved}", flush=True)
    return jsonify({"saved": saved})

# Non-blocking reindex start
@app.route("/reindex", methods=["POST"])
def reindex_start():
    started = start_worker(reindex_worker_incremental)
    if started:
        set_progress(task="reindex", state="queued", message="Worker started.", processed=0, total=0)
        return jsonify({"started": True, "message": "Reindexing started in background."})
    else:
        p = load_progress()
        return jsonify({"started": False, "message": f"Reindex already running: {p.get('state')}", "progress": p}), 202

@app.route("/status", methods=["GET"])
def status():
    return jsonify(load_progress())

@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    if not url:
        host = os.getenv("HOST_DOMAIN_WHITELIST", "novacool.com")
        url = f"https://{host}"
    started = start_worker(crawl_once, url)
    if started:
        return jsonify({"started": True, "message": f"Crawl started for {url}"})
    else:
        return jsonify({"started": False, "message": "Another job is running. Try again later."}), 202

# Ask endpoint (kept simple)
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Empty question"}), 400
    try:
        vecs = load_vecs()
        metas = load_meta()
        if vecs.shape[0] == 0:
            return jsonify({"error": "No indexed data yet."}), 400
        q_vec = openai_embeddings([question])[0]
        sims = np.dot(vecs, q_vec)
        top_idx = sims.argsort()[-TOP_K:][::-1]
        top_chunks = [metas[i] for i in top_idx]
        context = "\n\n".join(c["text"] for c in top_chunks)
        sources = list({c["file"] for c in top_chunks})
        key = os.getenv("OPENAI_API_KEY", "")
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": "You are Novacool’s knowledgeable assistant. Cite filenames when relevant."},
                    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
                ],
            },
            timeout=90,
        )
        r.raise_for_status()
        answer = r.json()["choices"][0]["message"]["content"]
        answer += f"\n\nSources: {', '.join(sources)}"
        return jsonify({"answer": answer})
    except Exception as e:
        print(f"❌ Ask error: {e}", flush=True)
        return jsonify({"error": f"Backend error: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
