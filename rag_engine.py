import os
import json
import numpy as np
import faiss
from PyPDF2 import PdfReader
import docx
import requests

DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "index.faiss")
META_PATH = os.path.join(DATA_DIR, "documents.json")
UPLOADS_DIR = "uploads"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_BASE = "https://api.openai.com/v1"


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def _extract_text_from_pdf(path):
    """Return list of (page_number, text) for a PDF."""
    texts = []
    try:
        reader = PdfReader(path)
    except Exception:
        return texts

    for i, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        texts.append((i + 1, t))
    return texts


def _extract_text_from_docx(path):
    """Return list with single (None, full_text) for DOCX."""
    try:
        d = docx.Document(path)
    except Exception:
        return []
    parts = [p.text for p in d.paragraphs]
    full = "\n".join(parts)
    return [(None, full)]


def load_documents():
    """Scan uploads/ and build a list of {source, page, text} docs."""
    ensure_dirs()
    docs = []
    for fname in os.listdir(UPLOADS_DIR):
        path = os.path.join(UPLOADS_DIR, fname)
        if not os.path.isfile(path):
            continue
        lower = fname.lower()
        if lower.endswith(".pdf"):
            for page_num, txt in _extract_text_from_pdf(path):
                if txt.strip():
                    docs.append({"source": fname, "page": page_num, "text": txt})
        elif lower.endswith(".docx"):
            for page_num, txt in _extract_text_from_docx(path):
                if txt.strip():
                    docs.append({"source": fname, "page": page_num, "text": txt})
        elif lower.endswith(".txt"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            if txt.strip():
                docs.append({"source": fname, "page": None, "text": txt})
    return docs


def _chunk_text(text, chunk_size=1000, overlap=200):
    """Simple character-based chunker with overlap."""
    text = text.replace("\r\n", "\n")
    chunks = []
    n = len(text)
    start = 0
    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
    return chunks


def _embed_texts(api_key, texts, model=None):
    """Call OpenAI embeddings endpoint for a list of strings."""
    if not texts:
        # Return an empty (0, dim) array; caller should handle
        return np.zeros((0, 768), dtype="float32")

    if model is None:
        model = EMBEDDING_MODEL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{OPENAI_BASE}/embeddings"

    # For now, send in a single batch. Can be extended to batching if needed.
    resp = requests.post(
        url,
        json={"model": model, "input": texts},
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json().get("data", [])
    emb = np.array([d["embedding"] for d in data], dtype="float32")
    return emb


def build_index_from_uploads(api_key, embedding_model=None):
    """Build FAISS index from everything in uploads/."""
    ensure_dirs()
    docs = load_documents()
    if not docs:
        raise RuntimeError("No documents found in uploads/")

    all_chunks = []
    meta = []

    for doc in docs:
        chunks = _chunk_text(doc["text"])
        for ch in chunks:
            meta.append(
                {
                    "source": doc["source"],
                    "page": doc["page"],
                    "text": ch,
                }
            )
            all_chunks.append(ch)

    if not all_chunks:
        raise RuntimeError("Documents found, but no non-empty chunks extracted.")

    emb = _embed_texts(api_key, all_chunks, model=embedding_model or EMBEDDING_MODEL)
    if emb.shape[0] == 0:
        raise RuntimeError("Failed to embed document chunks.")

    dim = emb.shape[1]

    # Build a cosine-similarity index via normalized inner product
    faiss.normalize_L2(emb)
    index = faiss.IndexFlatIP(dim)
    index.add(emb)

    # Save index + metadata
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {"documents": len(docs), "chunks": len(meta)}


def has_index():
    return os.path.exists(INDEX_PATH) and os.path.exists(META_PATH)


def query_index(api_key, question, k=6, embedding_model=None):
    """Return top-k metadata entries for a question."""
    if not has_index():
        return []

    ensure_dirs()
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    q_emb = _embed_texts(
        api_key, [question], model=embedding_model or EMBEDDING_MODEL
    )
    if q_emb.shape[0] == 0:
        return []

    faiss.normalize_L2(q_emb)
    D, I = index.search(q_emb, k)
    idxs = I[0]

    results = []
    for idx in idxs:
        if idx < 0 or idx >= len(meta):
            continue
        results.append(meta[idx])
    return results
