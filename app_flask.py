import os
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from rag_pipeline import RAGPipeline

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load RAG engine
rag = RAGPipeline()

@app.route("/")
def home():
    return jsonify({"status": "online", "message": "Novacool AI backend running"}), 200

# === CHAT ENDPOINT ===
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        # This renders the embedded chat UI
        return render_template("chat.html")

    data = request.json
    query = data.get("message", "").strip()

    if not query:
        return jsonify({"response": "⚠ Please enter a message."})

    answer = rag.query(query)
    return jsonify({"response": answer})

# === FILE UPLOADER ===
@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return jsonify({"error": "No files received"}), 400

    files = request.files.getlist("files")
    saved = []

    for f in files:
        path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(path)
        saved.append(f.filename)

    return jsonify({"uploaded": saved}), 200

# === REINDEX KNOWLEDGE BASE ===
@app.route("/reindex", methods=["POST"])
def reindex():
    rag.reindex()  # rebuild FAISS index from uploads folder
    return jsonify({"status": "success", "message": "Knowledge base rebuilt"}), 200

# === Serve static uploader dashboard ===
@app.route("/uploader")
def uploader():
    return send_from_directory("static", "upload.html")

# Health check
@app.route("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
