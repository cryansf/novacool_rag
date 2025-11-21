import os
import json
import numpy as np
import faiss
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

UPLOAD_DIR = "uploads"
DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "index/faiss.index")
MANIFEST_PATH = os.path.join(DATA_DIR, "index/manifest.json")
EMBED_MODEL = "all-MiniLM-L6-v2"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "index"), exist_ok=True)


class RAGPipeline:
    def __init__(self):
        self.model = SentenceTransformer(EMBED_MODEL)
        self.index = None
        self.documents = []

        if os.path.exists(INDEX_PATH) and os.path.exists(MANIFEST_PATH):
            self._load_index()

    # ------------------------------
    # Load FAISS index + manifest
    # ------------------------------
    def _load_index(self):
        self.index = faiss.read_index(INDEX_PATH)
        with open(MANIFEST_PATH, "r") as f:
            self.documents = json.load(f)

    # ------------------------------
    # Save FAISS index + manifest
    # ------------------------------
    def _save_index(self):
        faiss.write_index(self.index, INDEX_PATH)
        with open(MANIFEST_PATH, "w") as f:
            json.dump(self.documents, f, indent=2)

    # ------------------------------
    # Extract text from PDF or HTML
    # ------------------------------
    def extract_text(self, file_path):
        text = ""

        if file_path.lower().endswith(".pdf"):
            with fitz.open(file_path) as pdf:
                for page in pdf:
                    text += page.get_text()

        else:  # HTML / DOCX converted to HTML
            with open(file_path, "r", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
                text = soup.get_text(separator=" ")

        return text

    # ------------------------------
    # Embed + store document
    # ------------------------------
    def embed_and_store(self, filename):
        file_path = os.path.join(UPLOAD_DIR, filename)
        text = self.extract_text(file_path)
        chunks = [text[i:i + 500] for i in range(0, len(text), 500)]

        embeddings = self.model.encode(chunks)

        if self.index is None:
            self.index = faiss.IndexFlatL2(embeddings.shape[1])

        self.index.add(np.array(embeddings).astype("float32"))

        self.documents.extend(chunks)
        self._save_index()

        return len(chunks)

    # ------------------------------
    # Query search
    # ------------------------------
    def search(self, query, k=5):
        if self.index is None or len(self.documents) == 0:
            return []

        query_vec = self.model.encode([query]).astype("float32")
        scores, ids = self.index.search(query_vec, k)

        return [self.documents[i] for i in ids[0] if i < len(self.documents)]
