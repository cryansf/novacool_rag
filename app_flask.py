from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import hashlib
import json
from crawler_controller import CrawlerManager, register_crawler_routes

# LangChain & FAISS imports
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- App setup ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Initialize crawler ---
crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# --- Persistent disk paths ---
DATA_DIR = "/opt/render/project/data"
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
INDEX_DIR = os.path.join(DATA_DIR, "index")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)


# --- Utility: File hashing ---
def file_hash(path):
    """Return SHA256 hash of a file for change detection."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_existing_hashes():
    """Load known file hashes from manifest.json."""
    if not os.path.exists(MANIFEST_PATH):
        return {}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_hashes(hashes):
    """Persist updated manifest of file hashes."""
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)


# --- Incremental reindex function ---
def reindex_knowledge_base(new_files=None):
    """
    Incrementally index only new or modified files.
    Creates / updates FAISS index at /data/index.
    """
    print("🔍 Starting incremental reindex...")
    existing_hashes = load_existing_hashes()
    updated_hashes = dict(existing_hashes)
    changed_files = []

    files_to_scan = new_files or os.listdir(UPLOAD_FOLDER)
    for fname in files_to_scan:
        path = os.path.join(UPLOAD_FOLDER, fname)
        if not os.path.isfile(path):
            continue
        new_hash = file_hash(path)
        if existing_hashes.get(fname) != new_hash:
            changed_files.append(fname)
            updated_hashes[fname] = new_hash

    if not changed_files:
        print("✅ No new or modified files detected. Skipping reindex.")
        return "No new files to index."

    print(f"📄 Indexing {len(changed_files)} file(s): {changed_files}")

    # --- Load and chunk documents ---
    docs = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for fname in changed_files:
        path = os.path.join(UPLOAD_FOLDER, fname)
        if fname.lower().endswith(".pdf"):
            loader = PyPDFLoader(path)
        elif fname.lower().endswith(".docx"):
            loader = Docx2txtLoader(path)
        elif fname.lower().endswith(".txt"):
            loader = TextLoader(path)
        else:
            print(f"⚠️ Skipping unsupported file: {fname}")
            continue
        docs.extend(splitter.split_documents(loader.load()))

    # --- Generate embeddings and update FAISS index ---
    embeddings = OpenAIEmbeddings()
    index_path = os.path.join(INDEX_DIR, "faiss_index")

    if os.path.exists(index_path):
        db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        db.add_documents(docs)
    else:
        db = FAISS.from_documents(docs, embeddings)

    db.save_local(index_path)
    save_hashes(updated_hashes)

    print("✅ Incremental reindex complete.")
    return f"Indexed {len(changed_files)} new file(s)."


# --- Home route ---
@app.route("/")
def home():
    return "<h2>🔥 Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"


# --- File upload handler ---
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No file uploaded"}), 400

        saved_files = []
        for file in files:
            if file.filename:
                save_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(save_path)
                saved_files.append(file.filename)

        # 🔁 Incremental reindex only for new/changed files
        msg = reindex_knowledge_base(new_files=saved_files)

        return jsonify({"status": f"✅ Uploaded and indexed: {msg}"})

    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


# --- Reindex manually ---
@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"message": msg})


# --- Serve uploader dashboard ---
@app.route("/uploader")
def uploader():
    return send_from_directory("templates", "uploader.html")


# --- Crawl status (polled by frontend) ---
@app.route("/crawl_status")
def crawl_status():
    try:
        return jsonify({
            "active": crawler.active,
            "paused": crawler.paused,
            "stopped": crawler.stopped,
            "progress": crawler.progress,
            "status": crawler.status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Health check route ---
@app.route("/status")
def status():
    return jsonify({
        "status": "online",
        "crawler_active": crawler.active,
        "files_in_uploads": len(os.listdir(UPLOAD_FOLDER)),
        "index_size": len(os.listdir(INDEX_DIR)),
    })


# --- Run Flask app ---
if __name__ == "__main__":
    print("🚀 Starting Novacool RAG Flask Server on port 8080...")
    app.run(host="0.0.0.0", port=8080)
