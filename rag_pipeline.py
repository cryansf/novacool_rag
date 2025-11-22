import os
import numpy as np
import pandas as pd
import faiss
import openai
from sentence_transformers import SentenceTransformer
from glob import glob
import fitz  # PyMuPDF
from docx import Document

UPLOAD_DIR = "uploads"
DATA_DIR = "data"
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.index")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.csv")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# -------------------- EXTRACT TEXT --------------------
def extract_text(file_path):
    ext = file_path.lower()

    if ext.endswith(".pdf"):
        text = ""
        with fitz.open(file_path) as pdf:
            for page in pdf:
                text += page.get_text()
        return text

    elif ext.endswith(".docx"):
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    elif ext.endswith(".txt"):
        with open(file_path, "r", errors="ignore") as f:
            return f.read()

    return ""


# -------------------- REINDEX --------------------
def run_reindex():
    files = glob(os.path.join(UPLOAD_DIR, "*"))
    if not files:
        return "⚠️ No files found in uploads — please upload first."

    chunks = []
    sources = []

    for file in files:
        text = extract_text(file)
        if text:
            chunks.append(text)
            sources.append(os.path.basename(file))

    if not chunks:
        return "⚠️ Uploaded files could not be read."

    embeddings = embedding_model.encode(chunks).astype("float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, EMBEDDINGS_FILE)

    df = pd.DataFrame({"text": chunks, "source": sources})
    df.to_csv(METADATA_FILE, index=False)

    return f"Reindex complete — {len(chunks)} documents processed."


# -------------------- RAG RETRIEVAL + GENERATION --------------------
def answer_query(question):
    if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
        return "⚠️ No indexed documents found — upload and reindex first."

    df = pd.read_csv(METADATA_FILE)
    index = faiss.read_index(EMBEDDINGS_FILE)

    q_emb = embedding_model.encode(question).astype("float32")
    distances, idx = index.search(np.expand_dims(q_emb, 0), top_k=5)

    context = "\n\n".join(df.iloc[i]["text"] for i in idx[0] if 0 <= i < len(df))
    sources = ", ".join(df.iloc[i]["source"] for i in idx[0] if 0 <= i < len(df))

    prompt = f"""
You are Novacool UEF’s AI firefighting expert. Use ONLY the context below.

Context:
{context}

Question: {question}

If an answer cannot be confirmed by the context, say:
"⚠️ I do not have indexed material to answer that yet."
"""

    key = os.getenv("OPENAI_API_KEY", "")
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content + f"\n\n📌 Sources: {sources}"
