from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from crawler_controller import crawl_and_ingest  # your crawler logic
from rag_pipeline import generate_answer          # your RAG response function

# Initialize Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# --------------------------------------------------------
# ROUTES: Frontend Pages
# --------------------------------------------------------

@app.route("/")
def index():
    """Main home page."""
    return render_template("index.html")

@app.route("/uploader")
def uploader():
    """File upload page."""
    return render_template("uploader.html")

@app.route("/widget")
def widget():
    """Standalone chat widget (for embedding via iframe)."""
    return render_template("chat.html")

# --------------------------------------------------------
# ROUTE: Web crawler ingestion endpoint
# --------------------------------------------------------

@app.route("/crawl", methods=["POST"])
def crawl():
    """Crawl and ingest a given URL for knowledge base updates."""
    try:
        data = request.get_json()
        target_url = data.get("url")
        if not target_url:
            return jsonify({"status": "error", "message": "No URL provided"}), 400

        summary = crawl_and_ingest(target_url)
        return jsonify({"status": "success", "message": "Crawl complete", "summary": summary}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --------------------------------------------------------
# ROUTE: Chat API Endpoint
# --------------------------------------------------------

@app.route("/chat", methods=["POST"])
def chat_api():
    """Receive user message and return assistant response."""
    try:
        data = request.get_json(force=True)
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"response": "Please enter a message."})

        # ✅ Call your RAG or custom answer generator
        answer = generate_answer(message)
        return jsonify({"response": answer})

    except Exception as e:
        print(f"[ERROR] Chat route failed: {e}")
        return jsonify({"response": f"Error: {str(e)}"}), 500

# --------------------------------------------------------
# RAG fallback function (if rag_pipeline.py not found)
# --------------------------------------------------------

def generate_answer(prompt: str):
    """Fallback simple answer generator if rag_pipeline is unavailable."""
    default_facts = {
        "biodegradable": "Yes — Novacool UEF is fully biodegradable, non-toxic, and fluorine-free.",
        "pfas": "Novacool UEF contains no PFOS, PFOA, or fluorinated surfactants of any kind.",
        "classes": "Novacool can be used on Class A, B, D, and K fires — including 3D fuel fires.",
        "mix": "Typical mix ratios are 0.1% to 0.5%, depending on fuel type and application."
    }

    for key, value in default_facts.items():
        if key in prompt.lower():
            return value

    return (
        "Novacool UEF is a certified environmentally friendly firefighting agent, "
        "effective on multiple fire classes and approved under NFPA 18 standards."
    )

# --------------------------------------------------------
# SERVER ENTRY POINT
# --------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
