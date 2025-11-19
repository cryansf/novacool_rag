from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from rag_pipeline import answer_query   # <-- this is the only RAG function you need

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return "<h2>🔥 Novacool RAG backend is running successfully</h2>"

# === Full-page chat UI ===
@app.route("/chat", methods=["GET"])
def chat_page():
    return render_template("chat.html")

# === JSON API endpoint used by widget + chat UI ===
@app.route("/api/ask", methods=["POST"])
def api_ask():
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "Please enter a question."})

    try:
        answer = answer_query(question)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"answer": f"Error: {str(e)}"})

# === Health check for Render ===
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# === REQUIRED ENTRYPOINT FOR GUNICORN ===
if __name__ == "__main__":
    # Local debug mode — Render ignores this when using Gunicorn
    app.run(host="0.0.0.0", port=10000, debug=True)
