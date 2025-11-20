import os
from uuid import uuid4
import faiss
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from docx import Document
from PyPDF2 import PdfReader
import openai

# -------------------------
# CONFIGURATION
# -------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_DIR = "uploads"
DATA_DIR = "data"
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.faiss")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.csv")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# -------------------------
# FILE PARSING HELPERS
# -------------------------
def extract_text(file_path):
    text = ""
    try:
        if file_path.endswith(".pdf"):
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        elif file_path.endswith(".docx"):
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
    except Exception as e:
        print(f"⚠ Could not extract text from {file_path}: {e}")
    return text.strip()


def chunk_text(text, chunk_size=700):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


# -------------------------
# UPLOAD ENDPOINT
# -------------------------
@app.route("/upload", methods=["POST"])
def upload_files():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"message": "No files received"}), 400

    for f in files:
        save_path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(save_path)

    return jsonify({"message": f"{len(files)} file(s) uploaded successfully"})


# -------------------------
# REINDEX ENDPOINT
# -------------------------
@app.route("/reindex", methods=["GET"])
def reindex():
    try:
        print("🟦 Starting reindex...")
        files = os.listdir(UPLOAD_DIR)
        if not files:
            return jsonify({"error": "No uploaded files found — upload files first."}), 400

        embedding_list = []
        metadata_rows = []

        for file_name in files:
            file_path = os.path.join(UPLOAD_DIR, file_name)
            print(f"📄 Reading {file_name}")

            text = extract_text(file_path)
            if not text:
                print(f"⚠ Skipped empty/unreadable file {file_name}")
                continue

            chunks = chunk_text(text)
            for chunk in chunks:
                emb = embedding_model.encode(chunk)
                embedding_list.append(emb)
                metadata_rows.append({
                    "chunk_id": str(uuid4()),
                    "text": chunk,
                    "file": file_name
                })

        if len(embedding_list) == 0:
            return jsonify({"error": "No usable text extracted — try different PDFs/DOCX"}), 400

        df = pd.DataFrame(metadata_rows)
        df.to_csv(METADATA_FILE, index=False)

        vectors = np.vstack(embedding_list).astype("float32")
        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, EMBEDDINGS_FILE)

        print("✅ Reindex complete.")
        return jsonify({"status": "success", "chunks_indexed": len(metadata_rows)})

    except Exception as e:
        print("🔥 ERROR during reindex:", e)
        return jsonify({"error": str(e)}), 500


# -------------------------
# CHUNK RETRIEVAL
# -------------------------
def retrieve_chunks(question, top_k=5):
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


# -------------------------
# CHAT ENDPOINT
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    print("🔥 RECEIVED:", data)

    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"reply": "Please enter a question."})

    context = retrieve_chunks(query)

    prompt = f"""
You are the Novacool UEF expert assistant. Provide precise, technical, professional answers.

Context:
{context}

User question: {query}
"""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content.strip()
        return jsonify({"reply": answer})
    except Exception as e:
        print("🔥 OpenAI ERROR:", e)
        return jsonify({"reply": "⚠ AI backend error — please try again later."})


# -------------------------
# SERVE WIDGET UI
# -------------------------
@app.route("/static/<path:path>")
def static_file(path):
    return send_from_directory("static", path)


# -------------------------
# ROOT
# -------------------------
@app.route("/")
def home():
    return "Novacool RAG backend running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
