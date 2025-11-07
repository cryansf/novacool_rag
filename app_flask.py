from flask import Flask, render_template, request, jsonify
import os
import openai
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
app = Flask(__name__)

# Folder where uploads are stored temporarily
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Make sure your API key is set in Render > Environment Variables
openai.api_key = os.getenv("OPENAI_API_KEY")

# ----------------------------------------------------------------------------
# ROUTES
# ----------------------------------------------------------------------------

@app.route("/")
def index():
    return "<h2>Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

# --------------------------- FILE UPLOADER -----------------------------------

@app.route("/uploader")
def uploader_page():
    return render_template("uploader.html")

@app.route("/upload", methods=["POST"])
def upload_files():
    """
    Handles multiple file uploads and (placeholder) indexing.
    Replace the indexing section with your actual RAG chunking logic.
    """
    if "files" not in request.files:
        return "No files part in request", 400

    files = request.files.getlist("files")
    saved_files = []

    for file in files:
        if file.filename == "":
            continue
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        saved_files.append(save_path)

        # --- Example indexing placeholder (replace with your chunking code) ---
        if filename.lower().endswith(".pdf"):
            reader = PdfReader(save_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            # TODO: call your RAG indexer here with "text"
            print(f"Indexed PDF: {filename} ({len(text)} chars)")
        else:
            print(f"Saved file {filename} for indexing later")

    return jsonify({"status": f"{len(saved_files)} file(s) uploaded and indexed successfully."})

# ------------------------------- CHAT UI ------------------------------------

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/widget")
def widget_page():
    return render_template("widget.html")

# ------------------------------- CHAT API -----------------------------------

@app.route("/api/chat", methods=["POST"])
def chat_api():
    """
    Main chat endpoint for both /chat and /widget interfaces.
    """
    try:
        data = request.get_json(force=True)
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        # ---------------------------------------------------------------------
        # Call OpenAI (or your local RAG retrieval endpoint)
        # ---------------------------------------------------------------------
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Novacool’s RAG assistant. Be factual and concise."},
                {"role": "user", "content": user_message}
            ]
        )

        reply = response.choices[0].message["content"].strip()
        return jsonify({"reply": reply})

    except Exception as e:
        print("Chat API error:", e)
        return jsonify({"error": str(e)}), 500

# ------------------------------ MAIN ENTRY ----------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
