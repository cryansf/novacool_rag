import os

# Persistent root (Render uses /data). Falls back to local ./data
DATA_ROOT = os.getenv("DATA_ROOT", "/data") if os.path.isdir("/data") else os.path.abspath("data")

# Folders
UPLOAD_DIR = os.path.join(DATA_ROOT, "uploads")
INDEX_DIR = os.path.join(DATA_ROOT, "index")
META_PATH = os.path.join(INDEX_DIR, "meta.jsonl")
FAISS_PATH = os.path.join(INDEX_DIR, "faiss.index")

# Chunking
CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", 500))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 80))

# Embeddings
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Retrieval
TOP_K = int(os.getenv("TOP_K", 6))

# Misc
ALLOWED_EXTS = {".pdf", ".docx", ".txt"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)
