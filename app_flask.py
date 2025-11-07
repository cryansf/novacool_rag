from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import openai
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
from docx import Document
import requests

# LangChain components
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# Detect environment (Render vs local)
if os.getenv("RENDER"):
    UPLOAD_FOLDER = "/data/uploads"
    DB_FOLDER = "/data/chroma_db"
else:
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
    DB_FOLDER = os.path.join(os.getcwd(), "chroma_db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DB_FOLDER, exist_ok=True)

# Load OpenAI key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize embeddings + persistent Chroma database
embedding = OpenAIEmbeddings()
vectorstore = Chroma(persist_directory=DB_FOLDER, embedding_function=embedding)

# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return "<h2>Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

# -------------------------- FILE UPLOADER -----------------------------------

@app.route("/uploader")
def uploader_page():
    return render_template("uploader.html")

@app.route("/upload", methods=["POST"])
def upload_files():
    """Handles multiple file uploads and indexes PDFs/DOCX into the vectorstore."""
    if "files" not in request.files:
        return jsonify({"status": "No files found in request"}), 400

    files = request.files.getlist("files")
    saved_files = []
    total_chunks = 0

    for file in files:
        if not file.filename:
            continue
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        saved_files.append(save_path)
        print(f"Saved {filename}")

        text = ""
        try:
            if filename.lower().endswith(".pdf"):
                reader = PdfReader(save_path)
                for page in reader.pages:
                    text += page.extract_text() or ""
            elif filename.lower().endswith(".docx"):
                doc = Document(save_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"

            if text.strip():
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
                chunks = splitter.split_text(text)
                vectorstore.add_texts(chunks, metadatas=[{"source": filename}] * len(chunks))
                vectorstore.persist()
                total_chunks += len(chunks)
                print(f"Indexed {filename} into {len(chunks)} chunks.")
            else:
                print(f"No text extracted from {filename}")

        except Exception as e:
            print(f"Failed to process {filename}: {e}")

    return jsonify({
        "status": f"Uploaded {len(saved_files)} file(s), indexed {total_chunks} text chunks successfully."
    })

# -------------------------- REINDEX -----------------------------------------

@app.route("/reindex", methods=["POST"])
def reindex_all():
    """Rebuilds the vectorstore from all stored PDFs/DOCX files."""
    try:
        # Clear old index
        vectorstore.delete_collection()
        vectorstore.persist()
        total_chunks = 0

        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            text = ""

            if filename.lower().endswith(".pdf"):
                reader = PdfReader(filepath)
                for page in reader.pages:
                    text += page.extract_text() or ""
            elif filename.lower().endswith(".docx"):
                doc = Document(filepath)
                for para in doc.paragraphs:
                    text += para.text + "\n"

            if text.strip():
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
                chunks = splitter.split_text(text)
                vectorstore.add_texts(chunks, metadatas=[{"source": filename}] * len(chunks))
                total_chunks += len(chunks)

        vectorstore.persist()
        return jsonify({"status": f"Reindexed {total_chunks} chunks from documents successfully."})
    except Exception as e:
        print("Reindex error:", e)
        return jsonify({"status": f"Reindex failed: {e}"}), 500

# -------------------------- WEB CRAWLER (Placeholder) -----------------------

@app.route("/crawl", methods=["POST"])
def crawl_site():
    """Fetches a webpage and returns status (placeholder for future RAG)."""
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"status": "No URL provided"}), 400

        print(f"Starting crawl for: {url}")
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return jsonify({"status": f"Failed to fetch {url} (HTTP {resp.status_code})"}), 400

        text = resp.text[:2000]
        print(f"Crawled {len(resp.text)} characters from {url}")
        return jsonify({"status": f"Crawled {url} successfully ({len(resp.text)} chars)."})
    except Exception as e:
        print("Crawl error:", e)
        return jsonify({"status": f"Crawl failed: {e}"}), 500

# ----------------------------- CHAT UI --------------------------------------

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/widget")
def widget_page():
    return render_template("widget.html")

@app.route("/admin/uploader")
def admin_uploader_alias():
    return render_template("uploader.html")

# ----------------------------- CHAT API (RAG) -------------------------------

@app.route("/api/chat", methods=["POST"])
def chat_api():
    """Handles user chat and retrieves relevant document context from Chroma."""
    try:
        data = request.get_json(force=True)
        user_message = data.get("message", "").strip()
        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        qa = ConversationalRetrievalChain.from_llm(
            ChatOpenAI(model_name="gpt-4o-mini", temperature=0.2),
            retriever=retriever,
            return_source_documents=True
        )

        result = qa({"question": user_message, "chat_history": []})
        reply = result["answer"]

        # Optional: show sources in logs
        sources = [doc.metadata.get("source", "unknown") for doc in result.get("source_documents", [])]
        print(f"User: {user_message}")
        print(f"Sources: {sources}")

        return jsonify({"reply": reply})

    except Exception as e:
        print("Chat API error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------------------- MAIN -----------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
