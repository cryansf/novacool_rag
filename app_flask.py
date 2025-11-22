import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rag_pipeline import answer_query, run_reindex

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

#
# -------------------- HEALTH --------------------
#
@app.get("/health")
def health():
    return "OK", 200


#
# -------------------- CHAT --------------------
#
@app.post("/chat")
def chat():
    try:
        data = request.get_json(force=True)
        question = data.get("question", "").strip()
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        answer = answer_query(question)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"Chat backend error: {e}"}), 500


#
# -------------------- FILE UPLOAD --------------------
#
@app.post("/upload")
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(save_path)
    return jsonify({"message": f"Uploaded: {file.filename}"}), 200


#
# -------------------- REINDEX --------------------
#
@app.post("/reindex")
def reindex():
    try:
        msg = run_reindex()
        return jsonify({"message": msg}), 200
    except Exception as e:
        return jsonify({"error": f"Reindex error: {e}"}), 500


#
# -------------------- LIST UPLOADED FILES --------------------
#
@app.get("/files")
def list_files():
    files = os.listdir(UPLOAD_DIR)
    return jsonify({"files": files}), 200


#
# -------------------- DASHBOARD FRONTEND (STATIC) --------------------
#
@app.get("/uploader")
def file_dashboard():
    return send_from_directory("static", "uploader.html")


@app.get("/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


#
# -------------------- APP ENTRY --------------------
#
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
