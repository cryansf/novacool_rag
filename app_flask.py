import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

from rag_engine import build_index_from_uploads, query_index, has_index

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

# =========================
# 🔐 Environment Settings
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================
# 🚦 Health & Root
# =========================
@app.route("/")
def index():
    return "Novacool AI backend is running", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


# =========================
# 🌐 Full-Page Chat UI
# =========================
@app.route("/chat")
def chat_page():
    return render_template("chat.html")


# =========================
# 🧠 Ask Novacool AI (with RAG)
# =========================
@app.route("/ask", methods=["POST"])
def ask():
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "Missing OPENAI_API_KEY"}), 500

        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        # --- Retrieve context from vector index (if present) ---
        context_blocks = []
        if has_index():
            try:
                docs = query_index(
                    OPENAI_API_KEY,
                    question,
                    k=6,
                    embedding_model=EMBEDDING_MODEL,
                )
                for d in docs:
                    src = d.get("source") or "Unknown"
                    page = d.get("page")
                    pg_str = f" (page {page})" if page else ""
                    snippet = d.get("text", "")[:1200]
                    context_blocks.append(
                        f"Source: {src}{pg_str}\n{snippet}"
                    )
            except Exception as e:
                # Fail gracefully: RAG off, but chat still works
                print("RAG query error:", e)

        context_text = ""
        if context_blocks:
            context_text = (
                "The following information is from Novacool UEF "
                "documents, training materials, certifications, and related data.\n\n"
                + "\n\n---\n\n".join(context_blocks)
            )

        # --- Call OpenAI Chat Completions API ---
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Novacool AI, an assistant for SW Firefighting Foam "
                    "& Equipment. You answer questions about Novacool UEF, its "
                    "mix ratios, applications, certifications, environmental profile, "
                    "and firefighting best practices.\n\n"
                    "If context is provided, you MUST base your answers ONLY on that "
                    "context. If the answer cannot be found in the context, say you "
                    "do not know or recommend contacting SW Firefighting Foam for "
                    "clarification. Do not guess."
                ),
            },
        ]

        if context_text:
            messages.append(
                {
                    "role": "system",
                    "content": "Here is the relevant Novacool context:\n\n" + context_text,
                }
            )

        messages.append({"role": "user", "content": question})

        payload = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.4,
        }

        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if not r.ok:
            try:
                err = r.json()
                msg = err.get("error", {}).get("message", r.text)
            except Exception:
                msg = r.text
            return jsonify({"error": f"OpenAI error: {msg}"}), 500

        resp = r.json()
        answer = (
            resp.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            return jsonify({"error": "Empty answer from OpenAI"}), 500

        return jsonify({"answer": answer}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 📚 Upload + Reindex
# =========================
@app.route("/upload", methods=["GET"])
def upload_page():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_files():
    if "files" not in request.files:
        return jsonify({"error": "No files"}), 400

    files = request.files.getlist("files")
    saved = []

    for file in files:
        filename = secure_filename(file.filename)
        if not filename:
            continue
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        saved.append(filename)

    return jsonify({"uploaded": saved}), 200


@app.route("/reindex", methods=["POST"])
def reindex():
    if not OPENAI_API_KEY:
        return jsonify({"error": "Missing OPENAI_API_KEY"}), 500

    try:
        result = build_index_from_uploads(
            OPENAI_API_KEY,
            embedding_model=EMBEDDING_MODEL,
        )
        return jsonify(
            {
                "status": "Reindex complete",
                "documents": result.get("documents"),
                "chunks": result.get("chunks"),
            }
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# 🔥 Local Dev Only
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
