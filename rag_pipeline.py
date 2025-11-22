import os
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
from glob import glob

UPLOAD_DIR = "uploads"
DATA_DIR = "data"
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.index")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.csv")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def retrieve_relevant_chunks(question, top_k=5):
    """Return best-matching text chunks, or empty list if no index exists."""
    if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
        return []

    df = pd.read_csv(METADATA_FILE)
    index = faiss.read_index(EMBEDDINGS_FILE)

    q_emb = embedding_model.encode(question).astype("float32")
    distances, idx = index.search(np.expand_dims(q_emb, 0), top_k)

    results = []
    for i in idx[0]:
        if 0 <= i < len(df):
            results.append({"text": df.iloc[i]["text"], "source": df.iloc[i]["source"]})
    return results


def reindex_all_files():
    """Rebuilds the embeddings index using all documents in /uploads."""
    files = glob(os.path.join(UPLOAD_DIR, "*"))
    if not files:
        return "⚠ No files in uploads — please upload first."

    chunks = []
    sources = []
    for file in files:
        try:
            with open(file, "r", errors="ignore") as f:
                text = f.read()
                chunks.append(text)
                sources.append(os.path.basename(file))
        except Exception:
            continue

    embeddings = embedding_model.encode(chunks).astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, EMBEDDINGS_FILE)

    df = pd.DataFrame({"text": chunks, "source": sources})
    df.to_csv(METADATA_FILE, index=False)

    return f"Reindex complete — {len(chunks)} files processed."
