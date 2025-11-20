import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_pipeline import add_files_to_knowledge_base, reindex_knowledge_base, answer_query

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)


# === HEALTH CHECK ===
@app.route("/", methods=["GET"])
def home():
    return "Novacool RAG backend running"


# === CHAT ENDPOINT (called by widget) ===
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        print("🔥 RECEIVED PAYLOAD:", data)

        # Accept all possible widget keys — including the real one ("query")
        question = (
            (data.get("query") if isinstance(data, dict) else None)
            or (data.get("question") if isinstance(data, dict) else None)
            or (data.get("message") if isinstance(data, dict) else None)
            or (data.get("input") if isinstance(data, dict) else None)
            or (data.get("text") if isinstance(data, dict) else None)
            or (data.get("prompt") if isinstance(data, dict) else None)
            or ""
        ).strip()

        if not question:
            return jsonify({"answer": "Please enter a question."})

        answer = answer_query(question)   # ← full RAG pipeline call
        return jsonify({"answer": answer})

    except Exception as e:
        print("❌ CHAT ERROR:", e)
        return jsonify({"answer": "System error — please try again later."}), 500


# === FILE UPLOAD (POST) ===
@app.route("/upload", methods=["POST"])
def upload_files():
    try:
        files = request.files.getlist("files")
        add_files_to_knowledge_base(files)
        return jsonify({"message": f"{len(files)} file(s) uploaded successfully"})
    except Exception as e:
        print("❌ UPLOAD ERROR:", e)
        return jsonify({"message": "Upload failed"}), 500


# === REINDEX KNOWLEDGE BASE (POST) ===
@app.route("/reindex", methods=["POST"])
def reindex():
    try:
        reindex_knowledge_base()
        return jsonify({"message": "Reindex complete"})
    except Exception as e:
        print("❌ REINDEX ERROR:", e)
        return jsonify({"message": "Reindex failed"}), 500


# === DASHBOARD VIEW FOR UPLOADING (GET) ===
@app.route("/upload", methods=["GET"])
def upload_dashboard():
    return app.send_static_file("upload.html")


# === SERVE CHAT UI (iframe loads this) ===
@app.route("/chat", methods=["GET"])
def chat_ui():
    return app.send_static_file("chat.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
