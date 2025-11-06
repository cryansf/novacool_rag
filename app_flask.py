import os, re, json, time, math, requests, numpy as np
from flask import Flask, request, jsonify, render_template, send_from_directory
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader

DATA_DIR = "/data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
META_FILE = os.path.join(DATA_DIR, "meta.json")
VECS_FILE = os.path.join(DATA_DIR, "vecs.npy")

TOP_K = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-large"

os.makedirs(UPLOAD_DIR, exist_ok=True)
app = Flask(__name__, template_folder="templates")

def normspace(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
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

def _sleep_backoff(try_idx, retry_after=None):
    if retry_after:
        try:
            wait = float(retry_after)
            time.sleep(min(wait, 20.0))
            return
        except Exception:
            pass
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
            return [x["embedding"] for x in r.json()["data"]]
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error on embeddings (attempt {attempt+1}): {e}", flush=True)
            _sleep_backoff(attempt)
    raise RuntimeError("Embedding failed after retries")

def save_meta(m): json.dump(m, open(META_FILE, "w", encoding="utf8"))
def load_meta(): return json.load(open(META_FILE)) if os.path.exists(META_FILE) else []
def save_vecs(v): np.save(VECS_FILE, np.array(v, dtype=np.float32))
def load_vecs(): return np.load(VECS_FILE) if os.path.exists(VECS_FILE) else np.zeros((0, 3072), dtype=np.float32)

@app.route("/")
def home(): return render_template("widget.html")

@app.route("/widget")
def widget(): return render_template("widget.html")

@app.route("/admin/uploader")
def uploader(): return render_template("uploader.html")

@app.route("/uploads/<path:filename>")
def get_upload(filename): return send_from_directory(UPLOAD_DIR, filename)

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

@app.route("/reindex", methods=["POST"])
def reindex():
    print("🧩 Starting reindex...", flush=True)
    texts, metas = [], []
    total_files = len(os.listdir(UPLOAD_DIR))
    print(f"📁 Found {total_files} files to process.", flush=True)

    for fn in os.listdir(UPLOAD_DIR):
        fp = os.path.join(UPLOAD_DIR, fn)
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
            continue

        for chunk in chunk_text(text):
            metas.append({"file": fn, "text": chunk})
            texts.append(chunk)

    total_chunks = len(texts)
    if not texts:
        print("⚠️ No text found in uploaded files.", flush=True)
        return jsonify({"error": "No files found"}), 400

    print(f"🧮 Total chunks to embed: {total_chunks}", flush=True)
    batch_size = 25
    all_vecs = []
    batches = math.ceil(total_chunks / batch_size)

    for i in range(0, total_chunks, batch_size):
        batch = texts[i:i+batch_size]
        batch_num = i // batch_size + 1
        print(f"📦 Embedding batch {batch_num}/{batches} ({len(batch)} chunks)...", flush=True)
        for retry in range(5):
            try:
                vecs = openai_embeddings(batch)
                all_vecs.extend(vecs)
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
        batch.clear()
        del batch
    save_meta(metas)
    save_vecs(all_vecs)
    print(f"🎉 Reindex complete: {len(all_vecs)} chunks embedded successfully.", flush=True)
    return jsonify({"reindexed_chunks": len(all_vecs)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
