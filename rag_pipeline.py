import os
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer
import openai
from glob import glob

# === CONSTANT PATHS ===
UPLOAD_DIR = "uploads"
DATA_DIR = "data"
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.index")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.csv")

os.makedirs(DATA_DIR, exist_ok=True)

# === EMBEDDING MODEL ===
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# ==========================================================
#  RAG — CHUNK RETRIEVAL
# ==========================================================
def retrieve_relevant_chunks(question, top_k=5):
    if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
        return ""

    df = pd.read_csv(METADATA_FILE)
    index = faiss.read_index(EMBEDDINGS_FILE)

    q_emb = embedding_model.encode(question).astype("float32")
    distances, idx = index.search(np.expand_dims(q_emb, 0), top_k)

    results = []
    for i in idx[0]:
        if 0 <= i < len(df):
            results.append(df.iloc[i]["text"])

    return "\n\n".join(results)


# ==========================================================
#  RAG — QUERY ANSWERING
# ==========================================================
def answer_query(question):
    """
    Retrieves relevant indexed context and asks OpenAI for an answer.
    """
    context = retrieve_relevant_chunks(question)

    if not context:
        return "⚠️ No indexed documents match this query yet — please upload and reindex."

    prompt = f"""
You are Novacool UEF's technical expert. Use only the context below to answer.

Context:
{context}

Question: {question}
"""
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


# ==========================================================
#  RAG — REINDEX (RESTORES BACKEND)
# ==========================================================
def run_reindex():
    """
    Rebuilds FAISS embeddings based on all documents in /uploads.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    files = glob(os.path.join(UPLOAD_DIR, "*"))
    if not files:
        return "⚠️ No files found in uploads — please upload first."

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

    if not chunks:
        return "⚠️ Upload files could not be read."

    embeddings = embedding_model.encode(chunks).astype("float32")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, EMBEDDINGS_FILE)

    df = pd.DataFrame({"text": chunks, "source": sources})
    df.to_csv(METADATA_FILE, index=False)

    return f"Reindex complete — {len(chunks)} documents processed."
