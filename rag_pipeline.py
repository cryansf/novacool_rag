import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# -------------------------------------------------------------------
# Persistent paths
# -------------------------------------------------------------------
DATA_DIR = "/data/vector_store"
os.makedirs(DATA_DIR, exist_ok=True)

EMBED_FILE = os.path.join(DATA_DIR, "embeddings.npy")
META_FILE = os.path.join(DATA_DIR, "metadata.json")
INDEX_FILE = os.path.join(DATA_DIR, "faiss.index")

# Load or initialize global model and data
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = None
metadata = []
index = None


# -------------------------------------------------------------------
# Load or initialize FAISS index
# -------------------------------------------------------------------
def load_index():
    global embeddings, metadata, index

    if os.path.exists(EMBED_FILE) and os.path.exists(META_FILE) and os.path.exists(INDEX_FILE):
        print("[RAG] Loading existing FAISS index...")
        embeddings = np.load(EMBED_FILE)
        with open(META_FILE, "r", encoding="utf-8") as f:
            metadata.extend(json.load(f))
        index = faiss.read_index(INDEX_FILE)
    else:
        print("[RAG] Creating new FAISS index...")
        index = faiss.IndexFlatL2(384)  # embedding size for MiniLM
        embeddings = np.empty((0, 384), dtype="float32")


# Initialize index on import
load_index()


# -------------------------------------------------------------------
# Ingest Text into RAG Store
# -------------------------------------------------------------------
def ingest_text(text, source="manual"):
    """Convert text to embeddings and store persistently."""
    global embeddings, metadata, index

    if not text.strip():
        return "No text provided for ingestion."

    vector = model.encode([text])
    index.add(vector.astype("float32"))

    # Update metadata
    metadata.append({"source": source, "text": text[:500]})
    embeddings = np.vstack([embeddings, vector])

    # Save everything
    np.save(EMBED_FILE, embeddings)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    faiss.write_index(index, INDEX_FILE)

    print(f"[RAG] Ingested text from: {source}")
    return f"Ingested {len(text)} characters from {source}"


# -------------------------------------------------------------------
# Query Text (semantic search)
# -------------------------------------------------------------------
def query_text(query, top_k=3):
    """Perform a semantic search against the FAISS index."""
    if index is None or index.ntotal == 0:
        return [{"text": "No documents have been indexed yet."}]

    query_vec = model.encode([query]).astype("float32")
    D, I = index.search(query_vec, top_k)

    results = []
    for i in range(len(I[0])):
        idx = I[0][i]
        if idx < len(metadata):
            results.append({
                "text": metadata[idx]["text"],
                "source": metadata[idx]["source"],
                "score": float(D[0][i])
            })
    return results
