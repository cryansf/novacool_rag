import os
import fitz  # PyMuPDF
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
from glob import glob
import openai

UPLOAD_DIR = "uploads"
DATA_DIR = "data"
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.index")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.csv")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# ==========================================
# 🔁 REINDEX EVERYTHING
# ==========================================
def reindex_all():
    files = glob(os.path.join(UPLOAD_DIR, "*"))
    if not files:
        return "⚠️ No uploaded files found."

    docs = []
    sources = []

    for file in files:
        try:
            text = extract_text(file)
            docs.append(text)
            sources.append(os.path.basename(file))
        except:
            continue

    if not docs:
        return "⚠️ Could not extract text from uploaded files."

    embeddings = embedding_model.encode(docs).astype("float32")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, EMBEDDINGS_FILE)

    df = pd.DataFrame({"text": docs, "source": sources})
    df.to_csv(METADATA_FILE, index=False)

    return f"✔ Reindex complete — {len(docs)} files processed."


# ==========================================
# 🔍 SEARCH + ANSWER
# ==========================================
def search(question):
    try:
        if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
            return {"answer": "⚠️ No indexed documents — please upload and reindex."}

        df = pd.read_csv(METADATA_FILE)
        index = faiss.read_index(EMBEDDINGS_FILE)

        q_emb = embedding_model.encode(question).astype("float32")
        distances, idx = index.search(np.expand_dims(q_emb, 0), 5)

        results = []
        for i in idx[0]:
            if 0 <= i < len(df):
                results.append(df.iloc[i]["text"])

        context = "\n\n".join(results)
        prompt = f"Use ONLY the context below to answer.\n\nContext:\n{context}\n\nQuestion: {question}"

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content.strip()

        return {"answer": answer}

    except Exception as e:
        return {"error": str(e)}


# ==========================================
# 🔽 SUPPORTED FILE TYPES
# ==========================================
def extract_text(file):
    name = file.lower()
    if name.endswith(".pdf"):
        return extract_pdf(file)
    if name.endswith(".docx"):
        return extract_docx(file)
    if name.endswith(".txt"):
        return open(file, "r", errors="ignore").read()
    return ""


def extract_pdf(path):
    text = ""
    with fitz.open(path) as pdf:
        for page in pdf:
            text += page.get_text()
    return text


def extract_docx(path):
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)
