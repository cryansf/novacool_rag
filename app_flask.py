from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_pipeline import search, reindex_all

app = Flask(__name__)
CORS(app)

# health check
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"answer": "⚠️ No question received"}), 400

    result = search(question)
    return jsonify(result)

# reindex endpoint
@app.route("/reindex", methods=["POST"])
def reindex():
    message = reindex_all()
    return jsonify({"message": message})

# uploader endpoint
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "⚠️ No file uploaded"}), 400

    file = request.files["file"]
    save_path = f"uploads/{file.filename}"
    file.save(save_path)
    return jsonify({"message": f"✔ Uploaded {file.filename}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
