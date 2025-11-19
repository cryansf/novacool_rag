import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import rag_pipeline as rag

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.getcwd(), "data")
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")


# ==========================
# HEALTH CHECK (Render)
# ==========================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# ==========================
# CHAT ENDPOINT (used by widget)
# ==========================
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        question = data.get("message", "").strip()

        if not question:
            return jsonify({"answer": "Please enter a question."})

        # Call your RAG function directly
        answer = rag.answer_query(question)

        return jsonify({"answer": answer})

    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"answer": "System error — please try again later."}), 500


# ==========================
# UPLOAD DOCUMENTS
# ==========================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "no file uploaded"}), 400

        file = request.files["file"]
        save_path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(save_path)

        return jsonify({"status": "success", "file": file.filename})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================
# REINDEX KNOWLEDGE BASE
# ==========================
@app.route("/reindex", methods=["POST"])
def reindex():
    try:
        rag.reindex_knowledge_base()
        return jsonify({"status": "success", "message": "Knowledge base rebuilt"})

    except Exception as e:
        print("REINDEX ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================
# HOME
# ==========================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Novacool RAG backend running"}), 200


# ==========================
# MAIN ENTRY
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
