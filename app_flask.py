import os
import re
import json
import requests
import numpy as np

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_from_directory,
)
from bs4 import BeautifulSoup
from docx import Document
from PyPDF2 import PdfReader

# === Paths & basic config ===
DATA_DIR = "data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
META_FILE = os.path.join(DATA_DIR, "meta.json")
VECS_FILE = os.path.join(DATA_DIR, "vecs.npy")

TOP_K = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"

app = Flask(__name__, template_folder="templates")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# === Utility helpers ===

def normspace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    t = normspace(text)
    if not t:
        return []
    out = []
    start = 0
    L = len(t)
    while start < L:
        end = min(L, start + size)
        out.append(t[start:end])
        if end == L:
            break
        start = end - overlap
    return out


def get_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return key


def openai_embeddings(texts):
    """
    Call OpenAI's embeddings endpoint directly via requests.
    """
    key = get_openai_key()
    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={"model": EMBED_MODEL, "input": texts},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return [d["embedding"] for d in data["data"]]


def openai_chat(messages):
    """
    Call OpenAI's chat completion endpoint directly via requests.
    """
    key = get_openai_key()
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": CHAT_MODEL,
            "messages": messages,
            "temperature": 0.3,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def save_meta(metas):
    with open(META_FILE, "w", encoding="utf8") as f:
        json.dump(metas, f, ensure_ascii=False, indent=2)


def load_meta():
    if not os.path.exists(META_FILE):
        return []
    with open(META_FILE, encoding="utf8") as f:
        return json.load(f)


def save_vecs(vecs):
    arr = np.array(vecs, dtype=np.float32)
    np.save(VECS_FILE, arr)


def load_vecs():
    if not os.path.exists(VECS_FILE):
        # 1536 is the dimension of text-embedding-3-small
        return np.zeros((0, 1536), dtype=np.float32)
    return np.load(VECS_FILE)


def semantic_search(query: str, top_k: int = TOP_K):
    vecs = load_vecs()
    metas = load_meta()
    if vecs.shape[0] == 0 or not metas:
        return [], []

    q_vec = np.array(openai_embeddings([query])[0], dtype=np.float32)

    # cosine similarity
    vec_norms = np.linalg.norm(vecs, axis=1) + 1e-8
    q_norm = np.linalg.norm(q_vec) + 1e-8
    sims = (vecs @ q_vec) / (vec_norms * q_norm)

    idxs = np.argsort(-sims)[:top_k]
    best_chunks = [metas[int(i)]["text"] for i in idxs]
    best_files = [metas[int(i)]["file"] for i in idxs]
    return best_chunks, best_files


# === Routes: pages ===

@app.route("/")
def home():
    # chat.html is your main UI
    return render_template("chat.html")


@app.route("/widget")
def widget():
    return render_template("widget.html")


@app.route("/admin/uploader")
def uploader():
    return render_template("uploader.html")


# === Static uploads ===

@app.route("/uploads/<path:filename>")
def get_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# === API: upload & reindex ===

@app.route("/upload", methods=["POST"])
def upload():
    """
    Accept multiple files, save them to data/uploads.
    """
    files = request.files.getlist("files")
    saved = []
    for f in files:
        if not f.filename:
            continue
        path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(path)
        saved.append(f.filename)
    return jsonify({"saved": saved})


@app.route("/reindex", methods=["POST"])
def reindex():
    """
    Scan data/uploads for .txt, .pdf, .docx; chunk, embed, and save vectors+metadata.
    """
    texts = []
    metas = []

    for fn in os.listdir(UPLOAD_DIR):
        fp = os.path.join(UPLOAD_DIR, fn)
        if not os.path.isfile(fp):
            continue

        lower = fn.lower()
        if lower.endswith(".txt"):
            with open(fp, encoding="utf8", errors="ignore") as f:
                text = f.read()
        elif lower.endswith(".pdf"):
            reader = PdfReader(fp)
            text = " ".join((page.extract_text() or "") for page in reader.pages)
        elif lower.endswith(".docx"):
            doc = Document(fp)
            text = " ".join(p.text for p in doc.paragraphs)
        else:
            continue

        for chunk in chunk_text(text):
            metas.append({"file": fn, "text": chunk})
            texts.append(chunk)

    if not texts:
        return jsonify({"error": "No files found in uploads/"}), 400

    vecs = openai_embeddings(texts)
    save_meta(metas)
    save_vecs(vecs)

    return jsonify(
        {"message": "Reindex complete", "chunks": len(vecs), "files_indexed": len(set(m["file"] for m in metas))}
    )


# === Optional: simple crawl endpoint ===

@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "https://novacool.com")
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for s in soup(["script", "style"]):
            s.extract()
        text = normspace(soup.get_text())
        chunks = chunk_text(text)
        if not chunks:
            return jsonify({"error": "No text found on page"}), 400

        vecs = openai_embeddings(chunks)
        metas = [{"file": f"Crawl:{url}", "text": c} for c in chunks]

        old_m, old_v = load_meta(), load_vecs()
        save_meta(old_m + metas)

        if old_v.shape[0] > 0:
            all_vecs = np.vstack([old_v, np.array(vecs, dtype=np.float32)])
        else:
            all_vecs = np.array(vecs, dtype=np.float32)
        save_vecs(all_vecs)

        return jsonify({"message": "Crawl complete", "chunks": len(chunks)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Core: /chat endpoint used by your website ===

@app.route("/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint expected by your website:
    - Request JSON: { "query": "user question" }
    - Response JSON: { "answer": "...", "sources": ["file1", "file2", ...] }
    """
    data = request.get_json(silent=True) or {}
    question = (data.get("query") or "").strip()
    if not question:
        return jsonify({"error": "Empty query"}), 400

    try:
        chunks, files = semantic_search(question)
        context_block = ""
        if chunks:
            joined = "\n\n---\n\n".join(chunks)
            context_block = f"Use the following Novacool knowledge base excerpts to answer:\n\n{joined}\n\n"

        system_msg = (
            "You are the Novacool UEF technical assistant. "
            "Answer clearly and concisely, focusing on firefighting foam, Novacool, and related topics. "
            "If the question is outside that domain, answer briefly but still helpfully."
        )

        user_content = context_block + f"Question: {question}"

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content},
        ]

        answer = openai_chat(messages)

        return jsonify(
            {
                "answer": answer,
                "sources": list(dict.fromkeys(files)),  # unique in order
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Optional: /ask alias for testing (curl) ===

@app.route("/ask", methods=["POST"])
def ask():
    """
    Convenience alias: accepts { "question": "..." } and calls the same logic as /chat.
    """
    data = request.get_json(silent=True) or {}
    q = (data.get("question") or data.get("query") or "").strip()
    if not q:
        return jsonify({"error": "Empty question"}), 400
    # Reuse /chat logic by faking a request object to it? Easier: call semantic_search + openai_chat again here.
    try:
        chunks, files = semantic_search(q)
        context_block = ""
        if chunks:
            joined = "\n\n---\n\n".join(chunks)
            context_block = f"Use the following Novacool knowledge base excerpts to answer:\n\n{joined}\n\n"

        system_msg = (
            "You are the Novacool UEF technical assistant. "
            "Answer clearly and concisely, focusing on firefighting foam, Novacool, and related topics."
        )

        user_content = context_block + f"Question: {q}"
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_content},
        ]
        answer = openai_chat(messages)
        return jsonify(
            {
                "answer": answer,
                "sources": list(dict.fromkeys(files)),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Simple healthcheck ===

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
