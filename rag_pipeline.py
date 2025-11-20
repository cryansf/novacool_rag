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

# ============================
# Persistent storage directories on Render
# ============================
UPLOAD_DIR = "/mnt/disk/uploads"
DATA_DIR = "/mnt/disk/data"
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.faiss")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.csv")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ============================
# Embedding model
# ============================
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# ============================
# Extract text from supported files
# ============================
def extract_text(file_path):
    text = ""
    if file_path.endswith(".pdf"):
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                chunk = page.extract_text()
                if chunk:
                    text += chunk + "\n"

    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"

    return text


# ============================
# Split large text into chunks for embedding
# ============================
def chunk_text(text, chunk_size=700):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


# ============================
# Add uploaded files to knowledge base folder
# ============================
def add_files_to_knowledge_base(files):
    for f in files:
        save_path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(save_path)


# ============================
# Reindex everything (convert text → embeddings → FAISS)
# ============================
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
            metadata_rows.append({
                "chunk_id": str(uuid4()),
                "text": chunk,
                "file": file_name
            })

    df = pd.DataFrame(metadata_rows)
    df.to_csv(METADATA_FILE, index=False)

    vectors = np.vstack(embedding_list).astype("float32")
    index = faiss.IndexFlatL2(vectors.shape[1])
    index.add(vectors)
    faiss.write_index(index, EMBEDDINGS_FILE)


# ============================
# Retrieve context relevant to a question
# ============================
def retrieve_relevant_chunks(question, top_k=5):
    if not os.path.exists(EMBEDDINGS_FILE) or not os.path.exists(METADATA_FILE):
        return ""

    df = pd.read_csv(METADATA_FILE)
    index = faiss.read_index(EMBEDDINGS_FILE)

    q_emb = embedding_model.encode(question).astype("float32")
    _, idx = index.search(np.expand_dims(q_emb, 0), top_k)

    results = []
    for i in idx[0]:
        if 0 <= i < len(df):
            results.append(df.iloc[i]["text"])

    return "\n\n".join(results)


# ============================
# Ask OpenAI using context from RAG
# ============================
def answer_query(question):
    context = retrieve_relevant_chunks(question)

    if not context:
        return "No indexed documents match this query yet — please upload and reindex."

    prompt = f"""
You are Novacool UEF's expert assistant. Using the context below,
answer the user's question accurately and concisely.

Context:
{context}

Question: {question}
"""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()
