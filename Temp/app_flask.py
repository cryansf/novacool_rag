import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from openai import OpenAI

from config import UPLOAD_DIR, TOP_K, OPENAI_API_KEY
from utils.io_helpers import safe_filename
from embedder import get_embeddings
from vectorstore import FaissStore

app = Flask(__name__, template_folder="templates")
CORS(app)

# 25 MB upload cap to prevent OOM on large files
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/upload")
def upload():
    # Accepts multiple files: key 'files'
    if 'files' not in request.files:
        return jsonify({"error": "No files in 'files' field"}), 400

    files = request.files.getlist('files')
    saved = []
    for f in files:
        if not f.filename:
            continue
        name = safe_filename(f.filename)
        ext = os.path.splitext(name)[1].lower()
        if ext not in {'.pdf', '.docx', '.txt'}:
            continue
        dst = os.path.join(UPLOAD_DIR, name)
        f.save(dst)
        saved.append(dst)

    if not saved:
        return jsonify({"saved": 0, "ingested": 0, "chunks": 0})

    from ingest import ingest_files  # local import to avoid cold-start cost
    stats = ingest_files(saved)
    return jsonify({"saved": len(saved), **stats})

@app.post("/reindex")
def reindex():
    # Force reindex of all files currently in UPLOAD_DIR
    paths = []
    for root, _, files in os.walk(UPLOAD_DIR):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in {'.pdf', '.docx', '.txt'}:
                paths.append(os.path.join(root, fn))
    if not paths:
        return jsonify({"added": 0, "chunks": 0})

    from ingest import ingest_files
    stats = ingest_files(paths)
    return jsonify(stats)

@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    q = data.get("message", "").strip()
    k = int(data.get("top_k", TOP_K))
    if not q:
        return jsonify({"error": "message is required"}), 400

    # Embed query → FAISS search
    q_emb = get_embeddings([q])
    store = FaissStore()
    hits = store.search(q_emb, k)

    context = "\n\n".join(
        [f"[Score {score:.3f}] ({m['source']}#{m['chunk']})\n{m.get('preview', '')}" for score, m in hits]
    )

    system = (
        "You are Novacool's technical assistant. Use the provided context to answer. "
        "If the answer isn't in context, say you don't know and suggest the closest relevant info."
    )

    user = (
        f"Question: {q}\n\n"
        f"Context (top {k}):\n{context if context else '[no context found]'}\n\n"
        f"Answer with clear steps and cite sources like (filename#chunk)."
    )

    if not client:
        return jsonify({
            "answer": "Server missing OPENAI_API_KEY. Set it and retry.",
            "sources": [m for _, m in hits]
        })

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
    )

    answer = resp.choices[0].message.content
    return jsonify({"answer": answer, "sources": [m for _, m in hits]})

@app.get("/")
def root():
    return render_template("chat.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
