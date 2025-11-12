import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from PyPDF2 import PdfReader

# === Configuration ===
DATA_DIR = "uploads"
INDEX_FILE = "data/knowledge_base.index"
MODEL_NAME = "all-MiniLM-L6-v2"

# === Initialize embedding model ===
embedding_model = SentenceTransformer(MODEL_NAME)
client = OpenAI()

# === Create or load FAISS index ===
def load_or_create_index():
    if os.path.exists(INDEX_FILE):
        index = faiss.read_index(INDEX_FILE)
        print(f"[RAG] Loaded existing FAISS index: {INDEX_FILE}")
    else:
        index = faiss.IndexFlatL2(384)
        print("[RAG] Created new FAISS index.")
    return index

index = load_or_create_index()
documents = []


# === Ingest text from PDF or DOCX ===
def ingest_text(file_path):
    global index, documents
    text = ""
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    elif file_path.endswith(".docx"):
        from docx import Document
        doc = Document(file_path)
        for p in doc.paragraphs:
            text += p.text + "\n"
    else:
        raise ValueError("Unsupported file type")

    if not text.strip():
        print(f"[RAG] Warning: No text extracted from {file_path}")
        return

    docs = [text[i:i+1000] for i in range(0, len(text), 1000)]
    embeddings = embedding_model.encode(docs)
    index.add(np.array(embeddings, dtype="float32"))
    documents.extend(docs)

    faiss.write_index(index, INDEX_FILE)
    print(f"[RAG] Indexed and saved: {file_path}")


# === Query text ===
def query_text(query):
    if index.ntotal == 0:
        print("[RAG] No indexed data found.")
        return "No results found."

    query_emb = embedding_model.encode([query])
    D, I = index.search(np.array(query_emb, dtype="float32"), 3)
    if len(I[0]) == 0:
        return "No results found."

    # Retrieve top matches
    results = [documents[i] for i in I[0] if i < len(documents)]
    context = " ".join(results)

    prompt = f"You are Novacool Assistant. Use the following context to answer:\n\n{context}\n\nQuestion: {query}\nAnswer:"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[RAG] Query failed: {e}")
        return f"Error: {e}"
