import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")  # <-- REQUIRED for sk-proj keys
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Create OpenAI client (supports sk and sk-proj keys)
client = OpenAI(
    api_key=OPENAI_API_KEY,
    project=OPENAI_PROJECT_ID if OPENAI_PROJECT_ID else None
)


@app.route("/")
def index():
    return "Novacool AI backend is running", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/chat")
def chat_page():
    return render_template("chat.html")


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Novacool AI, an assistant for SW Firefighting Foam & Equipment. "
                        "Answer clearly and concisely based on what you know about Novacool UEF, "
                        "its mix ratios, applications, certifications, environmental profile, "
                        "and firefighting best practices. If you don't know, say so."
                    ),
                },
                {"role": "user", "content": question},
            ],
            temperature=0.4,
        )

        answer = response.choices[0].message.content.strip()
        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
