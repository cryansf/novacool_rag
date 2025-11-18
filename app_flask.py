from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_pipeline import answer_query

app = Flask(__name__)
CORS(app)

@app.get("/health")
def health():
    return {"status": "ok"}, 200

@app.get("/")
def index():
    return jsonify({"message": "Novacool RAG backend running"}), 200

@app.post("/chat")
def chat():
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Missing field 'query'"}), 400
    
    try:
        result = answer_query(data["query"])
        return jsonify({"answer": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
