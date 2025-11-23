import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rag_pipeline import search, reindex_all

app = Flask(__name__)
CORS(app)

# ----------------------------
# 🔍 HEALTH CHECK
# ----------------------------
@app.route("/health")
def health():
    return "OK", 200


# ----------------------------
# 🤖 CHAT ENDPOINT
# ----------------------------
@app.route("/chat", methods=["POST"])
def chat_api():
    try:
        data = request.get_json(silent=True) or {}
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"answer": "⚠️ Please enter a question."})

        chunks = search(question)  # <<< IMPORTANT — no top_k parameter
        answer = chunks.get("answer", None)
        error = chunks.get("error", None)

        if error:
            return jsonify({"answer": f"⚠️ Backend error:\n{error}"})

        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"answer": f"⚠️ Fatal backend error:\n{str(e)}"})


# ----------------------------
# 📤 UPLOAD FILES
# ----------------------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload_route():
    if "file" not in request.files:
        return jsonify({"message": "No file uploaded"}), 400

    file = request.files["file"]
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(save_path)
    return jsonify({"message": f"Uploaded: {file.filename}"})


# ----------------------------
# 🔁 REINDEX DOCUMENTS
# ----------------------------
@app.route("/reindex", methods=["POST"])
def reindex_route():
    try:
        msg = reindex_all()
        return jsonify({"message": msg})
    except Exception as e:
        return jsonify({"message": f"Reindex error: {str(e)}"}), 500


# ----------------------------
# 🔗 STATIC FILES (chat UI)
# ----------------------------
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
