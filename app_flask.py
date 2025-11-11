import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from rag_pipeline import search_docs, ingest_text
from crawler_controller import crawl_and_ingest

# --- Initialize app ---
app = Flask(__name__)
CORS(app, origins=[
    "https://novacool.bubbleapps.io",
    "https://novacool.com",
    "https://www.novacool.com"
])

# --- OpenAI client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Data paths ---
DATA_DIR = "/data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

# --- ROUTES ---

@app.route("/")
def root():
    return jsonify({"status": "running", "message": "Novacool RAG backend is online 🚀"}), 200


@app.route("/health", methods=["GET"])
def health():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    """Handles chat messages coming from Bubble or other front-ends."""
    data = request.get_json()
    user_input = data.get("message", "")
    history = data.get("history", [])

    if not user_input:
        return jsonify({"error": "No input message provided"}), 400

    # Retrieve context from RAG search
    context_docs = search_docs(user_input)
    context_text = "\n".join([d["text"] for d in context_docs]) if context_docs else ""

    # Build the prompt
    messages = [
        {"role": "system", "content": "You are the Novacool UEF assistant. Answer factually and professionally about PFAS-free firefighting foam and equipment."},
        *history,
        {"role": "user", "content": f"{user_input}\n\nContext:\n{context_text}"}
    ]

    # Get completion from OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
    )

    reply = response.choices[0].message.content.strip()
    return jsonify({"reply": reply})


@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload a document (PDF, DOCX, TXT) and ingest it into the vector DB."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    save_path = os.path.join(DATA_DIR, file.filename)
    file.save(save_path)

    # Ingest text content into RAG vector database
    ingest_text(save_path)

    return jsonify({"message": f"File '{file.filename}' uploaded and ingested successfully"}), 200


@app.route("/reindex", methods=["POST"])
def reindex():
    """Re-crawls or re-indexes site content and refreshes the vector DB."""
    data = request.get_json(force=True)
    url = data.get("url", None)

    if not url:
        return jsonify({"error": "Missing URL for crawling"}), 400

    crawl_and_ingest(url)
    return jsonify({"message": f"Successfully crawled and indexed: {url}"}), 200


# --- Run locally (Render uses Gunicorn) ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
