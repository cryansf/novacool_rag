import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_pipeline import RAGPipeline

app = Flask(__name__)
CORS(app)

# ==========================
#   Load RAG Pipeline
# ==========================
DATA_DIR = os.path.join(os.getcwd(), "data")
rag_pipeline = RAGPipeline(data_path=DATA_DIR)

# ==========================
#   HEALTH CHECK
# ==========================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# ==========================
#   CHAT ENDPOINT (WIDGET)
# ==========================
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        user_input = data.get("message", "").strip()

        if not user_input:
            return jsonify({"answer": "Please enter a question."})

        # Retrieve RAG answer
        answer = rag_pipeline.query(user_input)

        # Return JSON response expected by the widget
        return jsonify({"answer": answer})

    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"answer": "System error — please try again later."}), 500


# ==========================
#   UPLOAD PDF/DOCX FOR INGESTION
# ==========================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "no file uploaded"}), 400

        file = request.files["file"]
        save_path = os.path.join(DATA_DIR, file.filename)
        file.save(save_path)

        return jsonify({"status": "success", "file": file.filename})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================
#   REINDEX KNOWLEDGE BASE
# ==========================
@app.route("/reindex", methods=["POST"])
def reindex():
    try:
        rag_pipeline.reindex(DATA_DIR)
        return jsonify({"status": "success", "message": "Knowledge base rebuilt"})

    except Exception as e:
        print("REINDEX ERROR:", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================
#   HOME
# ==========================
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Novacool RAG backend running"}), 200


# ==========================
#   MAIN ENTRY
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
