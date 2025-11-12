"""
rag_pipeline.py — Lightweight FAISS + SentenceTransformer pipeline
for Novacool RAG.  Optimized for low-memory Render environments.
"""

import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
from docx import Document

# === Globals ===
DATA_DIR = os.path.join(os.getcwd(), "data")
INDEX_FILE = os.path.join(DATA_DIR, "faiss.index")
TEXT_STORE = os.path.join(DATA_DIR, "texts.npy")
os.makedirs(DATA_DIR, exist_ok=True)

_model = None
_index = None
_texts = []


# === Lazy loaders ===

def get_model():
    """Load the SentenceTransformer model lazily."""
    global _model
    if _model is None:
        print("[RAG] Loading embedding model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_index():
    """Load or create FAISS index lazily."""
    global _index
    if _index is None:
        if os.path.exists(INDEX_FILE):
            print("[RAG] Loading existing FAISS index...")
            _index = faiss.read_index(INDEX_FILE)
        else:
            print("[RAG] Creating new FAISS index...")
            _index = faiss.IndexFlatL2(384)
    return _index


# === Utility: extract text ===

def extract_text(path):
    """Extract text from PDF or DOCX."""
    text = ""
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        for page in reader.pages:
            text += page.extract_text() or ""
    elif path.lower().endswith(".docx"):
        doc = Document(path)
        for p in doc.paragraphs:
            text += p.text + "\n"
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    return text.strip()


# === Ingest documents ===

def ingest_text(files):
    """Embed and store new documents."""
    model = get_model()
    index = get_index()
    global _texts

    new_embeddings = []
    for f in files:
        content = extract_text(f)
        if not content:
            continue
        emb = model.encode([content])[0].astype("float32")
        new_embeddings.append(emb)
        _texts.append(content)

    if not new_embeddings:
        return {"status": "no new text extracted"}

    embs = np.vstack(new_embeddings)
    index.add(embs)

    # Persist data
    faiss.write_index(index, INDEX_FILE)
    np.save(TEXT_STORE, np.array(_texts, dtype=object))
    print(f"[RAG] Added {len(new_embeddings)} document(s) to FAISS index.")

    return {"indexed_docs": len(new_embeddings)}


# === Query documents ===

def query_text(query, top_k: int = 3):
    """Return the most relevant text chunks for a query."""
    model = get_model()
    index = get_index()
    global _texts

    if os.path.exists(TEXT_STORE):
        _texts = np.load(TEXT_STORE, allow_pickle=True).tolist()

    if not _texts or index.ntotal == 0:
        return "Knowledge base is empty. Please upload documents first."

    q_emb = model.encode([query]).astype("float32")
    D, I = index.search(q_emb, top_k)

    results = [f"{_texts[i][:500]}..." for i in I[0] if i < len(_texts)]
    if not results:
        return "No relevant results found."

    return "\n\n---\n\n".join(results)


# === Optional: manual rebuild ===

def rebuild_index():
    """Recreate index from saved texts if index file is missing."""
    global _texts, _index
    model = get_model()
    if os.path.exists(TEXT_STORE):
        _texts = np.load(TEXT_STORE, allow_pickle=True).tolist()
        embs = model.encode(_texts).astype("float32")
        _index = faiss.IndexFlatL2(embs.shape[1])
        _index.add(embs)
        faiss.write_index(_index, INDEX_FILE)
        print(f"[RAG] Rebuilt FAISS index with {len(_texts)} docs.")
    else:
        print("[RAG] No stored texts found to rebuild index.")
