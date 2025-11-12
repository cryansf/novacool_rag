import os, json
from typing import List, Dict, Tuple
import numpy as np
import faiss
from config import INDEX_DIR, FAISS_PATH, META_PATH

class FaissStore:
    def __init__(self):
        self.index = None
        self.meta: List[Dict] = []
        self._load()

    # ---------- Persistence ----------
    def _load(self):
        if os.path.exists(FAISS_PATH) and os.path.exists(META_PATH):
            self.index = faiss.read_index(FAISS_PATH)
            with open(META_PATH, 'r', encoding='utf-8') as f:
                self.meta = [json.loads(line) for line in f]
        else:
            self.index = faiss.IndexFlatIP(1536)  # matches text-embedding-3-small dims
            self.meta = []

    def _save(self):
        os.makedirs(INDEX_DIR, exist_ok=True)
        faiss.write_index(self.index, FAISS_PATH)
        with open(META_PATH, 'w', encoding='utf-8') as f:
            for m in self.meta:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

    # ---------- Index Ops ----------
    def add(self, embeddings: np.ndarray, metadatas: List[Dict]):
        # Normalize to unit length for cosine via inner product
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.meta.extend(metadatas)
        self._save()

    def search(self, query_emb: np.ndarray, k: int) -> List[Tuple[float, Dict]]:
        faiss.normalize_L2(query_emb)
        D, I = self.index.search(query_emb, k)
        out = []
        for score, idx in zip(D[0].tolist(), I[0].tolist()):
            if idx == -1:
                continue
            out.append((score, self.meta[idx]))
        return out
