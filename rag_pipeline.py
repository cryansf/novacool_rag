from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import json
from pathlib import Path

DATA_DIR = Path("data/index")
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def ingest_text(text: str, source: str):
    """Save text chunks with embeddings for later retrieval."""
    embeddings = MODEL.encode([text])[0].tolist()
    record = {"source": source, "text": text, "embedding": embeddings}

    store = DATA_DIR / "knowledge_base.json"
    existing = json.loads(store.read_text()) if store.exists() else []
    existing.append(record)
    store.write_text(json.dumps(existing, indent=2))

def generate_answer(query: str) -> str:
    """Retrieve best matching text from stored knowledge and return summary."""
    kb_path = DATA_DIR / "knowledge_base.json"
    if not kb_path.exists():
        return "Knowledge base is empty. Please crawl or ingest some sources first."

    kb = json.loads(kb_path.read_text())
    q_embed = MODEL.encode([query])[0].reshape(1, -1)
    
    best_match = None
    best_score = -1
    for entry in kb:
        doc_embed = [entry["embedding"]]
        score = cosine_similarity(q_embed, doc_embed)[0][0]
        if score > best_score:
            best_score = score
            best_match = entry["text"]

    if not best_match:
        return "No relevant information found."
    
    return best_match[:600] + ("..." if len(best_match) > 600 else "")
