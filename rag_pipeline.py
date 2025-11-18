import os
import faiss
import numpy as np
import pandas as pd
from uuid import uuid4
from docx import Document
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_DIR = "uploads"
DATA_DIR = "data"
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.faiss")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.csv")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def extract_text(file_path):
    text = ""
    if file_path.endswith(".pdf"):
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text


def chunk_text(text, chunk_size=700):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


def add_files_to_knowledge_base(files):
    for f in files:
        save_path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(save_path)


def reindex_knowledge_base():
    embedding_list = []
    metadata_rows = []

    for file_name in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, file_name)
        text = extract_text(file_path)
        chunks = chunk_text(text)

        for chunk in chunks:
            emb = embedding_model.encode(chunk)
            embedding_list.append(emb)
            metadata_rows.append({"chunk_id": str(uuid4()), "text": chunk, "file": file_name})

    # Save metadata
    df = pd.DataFrame(metadata_rows)
    df.to_csv(METADATA_FILE, index=False)

    # Save embeddings to FAISS
    vectors = np.vstack(embedding_list).astype("float32")
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, EMBEDDINGS_FILE)


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
