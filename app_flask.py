import os, re, json, uuid, time, requests, numpy as np
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
EMBED_MODEL = "text-embedding-3-small"

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

def openai_embeddings(texts):
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={"model": EMBED_MODEL, "input": texts},
        timeout=60,
    )
    r.raise_for_status()
    return [x["embedding"] for x in r.json()["data"]]

def save_meta(m): 
    json.dump(m, open(META_FILE, "w", encoding="utf8"))

def load_meta(): 
    return json.load(open(META_FILE)) if os.path.exists(META_FILE) else []

def save_vecs(v): 
    np.save(VECS_FILE, np.array(v, dtype=np.float32))

def load_vecs(): 
    return np.load(VECS_FILE) if os.path.exists(VECS_FILE) else np.zeros((0, 1536), dtype=np.float32)

# ---------- ROUTES ----------
@app.route("/")
def home():
    # Show the main chat interface when visiting /
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
    return jsonify({"saved": saved})

# ---------- REINDEX ----------
@app.route("/reindex", methods=["POST"])
def reindex():
    texts, metas = [], []
    for fn in os.listdir(UPLOAD_DIR):
        fp = os.path.join(UPLOAD_DIR, fn)
        if fn.lower().endswith(".txt"):
            text = open(fp, encoding="utf8", errors="ignore").read()
        elif fn.lower().endswith(".pdf"):
            text = " ".join(page.extract_text() or "" for page in PdfReader(fp).pages)
        elif fn.lower().endswith(".docx"):
            doc = Document(fp)
            text = " ".join(p.text for p in doc.paragraphs)
        else:
            continue
        for chunk in chunk_text(text):
            metas.append({"file": fn, "text": chunk})
            texts.append(chunk)

    if not texts:
        return jsonify({"error": "No files found"}), 400

    vecs = openai_embeddings(texts)
    save_meta(metas)
    save_vecs(vecs)
    return jsonify({"reindexed_chunks": len(vecs)})

# ---------- CRAWL ----------
@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "https://novacool.com")
    log = []
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        text = normspace(soup.get_text())
        chunks = chunk_text(text)
        metas = [{"file": f"Crawl:{url}", "text": c} for c in chunks]
        vecs = openai_embeddings(chunks)
        old_m, old_v = load_meta(), load_vecs()
        save_meta(old_m + metas)
        all_vecs = np.vstack([old_v, np.array(vecs, dtype=np.float32)])
        save_vecs(all_vecs)
        log.append(f"Crawled {url} with {len(chunks)} chunks.")
        return jsonify({"message": "Crawl complete", "chunks": len(chunks), "log": log})
    except Exception as e:
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
                    {
                        "role": "system",
                        "content": "You are Novacool’s knowledgeable assistant. Cite filenames when relevant.",
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {question}",
                    },
                ],
            },
            timeout=90,
        )
        r.raise_for_status()
        answer = r.json()["choices"][0]["message"]["content"]
        answer += f"\n\nSources: {', '.join(sources)}"
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"Backend error: {e}"}), 500

# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
