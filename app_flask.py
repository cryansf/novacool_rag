from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from crawler_controller import CrawlerManager, register_crawler_routes

# -------------------------------
# App setup
# -------------------------------
app = Flask(__name__)
CORS(app)

crawler = CrawlerManager()
register_crawler_routes(app, crawler)

# -------------------------------
# Paths
# -------------------------------
DATA_DIR = "data"
UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# Home route
# -------------------------------
@app.route("/")
def home():
    return """
    <h2>Novacool RAG Deployment Active 🚀</h2>
    <ul>
      <li><a href="/uploader">Uploader Interface</a></li>
      <li><a href="/chat">Chat Assistant</a></li>
      <li><a href="/widget">Widget</a></li>
    </ul>
    """

# -------------------------------
# File upload route
# -------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)

    # Optional: could trigger reindex automatically later
    return jsonify({"message": f"{file.filename} uploaded successfully."})

# -------------------------------
# Reindex endpoint (stub)
# -------------------------------
def reindex_knowledge_base():
    # Placeholder for future integration with LangChain retraining
    return "Reindex complete (stub)."

@app.route("/reindex", methods=["POST"])
def reindex_route():
    msg = reindex_knowledge_base()
    return jsonify({"message": msg})

# -------------------------------
# Crawler status route
# -------------------------------
@app.route("/crawler_status")
def crawler_status():
    return jsonify({
        "active": crawler.active,
        "paused": crawler.paused,
        "stopped": crawler.stopped,
        "progress": crawler.progress,
        "status": crawler.status
    })

# -------------------------------
# Serve front-end interfaces
# -------------------------------
@app.route("/uploader")
def uploader():
    return send_from_directory("templates", "uploader.html")

@app.route("/chat")
def chat():
    # ✅ Make sure templates/chat.html exists!
    return send_from_directory("templates", "chat.html")

@app.route("/widget")
def widget():
    return "<h3>Novacool widget Active</h3><p>Endpoint will serve the embedded chat interface later.</p>"

# -------------------------------
# Run server
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
