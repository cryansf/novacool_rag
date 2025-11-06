import os, re, json, time, math, requests, numpy as np
from flask import Flask, request, jsonify, render_template, send_from_directory
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader

# ---------- CONFIG ----------
DATA_DIR = "/data"  # persistent disk mount path on Render
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
META_FILE = os.path.join(DATA_DIR, "meta.json")
VECS_FILE = os.path.join(DATA_DIR, "vecs.npy")

TOP_K = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
CHAT_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-large"  # higher accuracy

os.makedirs(UPLOAD_DIR, exist_ok=True)
app = Flask(__name__, template_folder="templates")

# ---------- UTILITIES ----------
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

# --- Robust embedding with retry & backoff (handles 429/5xx) ---
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

def save_meta(m): 
    json.dump(m, open(META_FILE, "w", encoding="utf8"))

def load_meta(): 
    return json.load(open(META_FILE)) if os.path.exists(META_FILE) else []

def save_vecs(v): 
    np.save(VECS_FILE, np.array(v, dtype=np.float32))

def load_vecs(): 
    return np.load(VECS_FILE) if os.path.exists(VECS_FILE) else np.zeros((0, 3072), dtype=np.float32)

# ---------- ROUTES ----------
@app.route("/")
def home():
    return render_template("widget.html")

@app.route("/widget")
def widget():
    return render_template("widget.html")

@app.route("/admin/uploader")
def uploader():
    return render_template("uploader.html")

@app.route("/uploads/<path:filename>")
def get_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# ---------- UPLOAD ----------
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

# ---------- REINDEX (Batch + Backoff + DOCX skip) ----------
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
    batch_size = 50  # smaller batches reduce 429s
    all_vecs = []
    batches = math.ceil(total_chunks / batch_size)

    for i in range(0, total_chunks, batch_size):
        batch = texts[i:i+batch_size]
        batch_num = i // batch_size + 1
        print(f"📦 Embedding batch {batch_num}/{batches} ({len(batch)} chunks)...", flush=True)
        try:
            vecs = openai_embeddings(batch)
            all_vecs.extend(vecs)
            print(f"✅ Completed batch {batch_num}/{batches}", flush=True)
        except Exception as e:
            print(f"❌ Error embedding batch {batch_num}: {e}", flush=True)
        time.sleep(0.5)

    save_meta(metas)
    save_vecs(all_vecs)
    print(f"🎉 Reindex complete: {len(all_vecs)} chunks embedded successfully.", flush=True)
    return jsonify({"reindexed_chunks": len(all_vecs)})

# ---------- CRAWL (Safe capped + backoff) ----------
@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "https://novacool.com")
    print(f"🌐 Crawling {url}...", flush=True)
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()

        # Extract visible text
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = normspace(soup.get_text())

        # Cap text at 10,000 characters
        if len(text) > 10000:
            print(f"⚠️ Page too long ({len(text)} chars) – truncating to 10,000.", flush=True)
            text = text[:10000]

        chunks = chunk_text(text)
        if not chunks:
            return jsonify({"error": "No text found"}), 400

        print(f"✅ Retrieved {len(text)} chars of text ({len(chunks)} chunks).", flush=True)

        # Retry embedding with backoff
        for attempt in range(5):
            try:
                vecs = openai_embeddings(chunks)
                break
            except Exception as e:
                print(f"⚠️ Embedding failed attempt {attempt+1}: {e}", flush=True)
                time.sleep(min(2**attempt, 16))
        else:
            return jsonify({"error": "Embedding failed after retries"}), 500

        metas = [{"file": f"Crawl:{url}", "text": c} for c in chunks]
        old_m, old_v = load_meta(), load_vecs()
        save_meta(old_m + metas)
        all_vecs = np.vstack([old_v, np.array(vecs, dtype=np.float32)])
        save_vecs(all_vecs)

        print(f"🎉 Crawl complete: {len(chunks)} chunks embedded.", flush=True)
        return jsonify({"message": "Crawl complete", "chunks": len(chunks)})
    except Exception as e:
        print(f"❌ Crawl error: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

# ---------- ASK ----------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Empty question"}), 400
    try:
        vecs, metas = load_vecs(), load_meta()
        if vecs.shape[0] == 0:
            return jsonify({"error": "No indexed data yet."}), 400

        q_vec = openai_embeddings([question])[0]
        sims = np.dot(vecs, q_vec)
        top_idx = sims.argsort()[-TOP_K:][::-1]
        top_chunks = [metas[i] for i in top_idx]
        context = "\n\n".join(c["text"] for c in top_chunks)
        sources = list({c["file"] for c in top_chunks})

        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500

        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": CHAT_MODEL,
                "messages": [
                    {"role": "system","content": "You are Novacool’s knowledgeable assistant. Cite filenames when relevant."},
                    {"role": "user","content": f"Context:\n{context}\n\nQuestion: {question}"},
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

# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
