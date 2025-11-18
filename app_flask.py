import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from rag_pipeline import embed_document, query_rag, reindex_knowledge_base

app = Flask(__name__)
CORS(app)

# -------------------------------
#  HEALTH CHECK (required by Render)
# -------------------------------
@app.route("/health")
def health():
    return "OK", 200


# -------------------------------
#  HOME → loads chat UI
# -------------------------------
@app.route("/")
def home():
    return render_template("chat.html")


# -------------------------------
#  CHAT ENDPOINT
# -------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message", "")

        # Run RAG pipeline
        response = query_rag(user_message)

        return jsonify({"reply": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------------
#  UPLOADER UI
# -------------------------------
@app.route("/upload")
def upload_ui():
    return render_template("uploader.html")


# -------------------------------
#  HANDLE DOC UPLOAD
# -------------------------------
@app.route("/upload", methods=["POST"])
def upload_files():
    try:
        files = request.files.getlist("files")
        for file in files:
            save_path = os.path.join("uploads", file.filename)
            file.save(save_path)

        return jsonify({"status": "success", "message": "Files uploaded"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# -------------------------------
#  REINDEX KNOWLEDGE BASE
# -------------------------------
@app.route("/reindex", methods=["POST"])
def reindex():
    try:
        reindex_knowledge_base()
        return jsonify({"status": "success", "message": "Reindex complete"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# -------------------------------
#  DEV TEST ENDPOINT
# -------------------------------
@app.route("/test")
def test():
    return jsonify({"message": "Backend running"}), 200


# -------------------------------
#  MAIN
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
