import os
from typing import List, Dict
from config import UPLOAD_DIR, CHUNK_TOKENS, CHUNK_OVERLAP
from utils.io_helpers import file_sha1, stamp
from utils.chunking import chunk_text
from parsers import any_to_text
from embedder import get_embeddings
from vectorstore import FaissStore

# Memory-safe ingestion: process embeddings in small batches to limit RAM.
BATCH_SIZE = 40  # env-tunable later if desired

def ingest_files(paths: List[str]) -> Dict:
    """Extract → chunk → embed → index. Returns summary stats."""
    store = FaissStore()

    total_chunks = 0
    files_added = 0

    for path in paths:
        text = any_to_text(path)
        if not text:
            continue

        chunks = chunk_text(text, CHUNK_TOKENS, CHUNK_OVERLAP)
        h = file_sha1(path)
        buf: List[str] = []
        metas: List[Dict] = []

        for i, ch in enumerate(chunks):
            buf.append(ch["text"])  # hold only BATCH_SIZE chunks
            metas.append({
                "source": os.path.basename(path),
                "sha1": h,
                "chunk": i,
                "created": stamp(),
                "rel_path": os.path.relpath(path, UPLOAD_DIR),
                "preview": ch["text"][:800],
            })

            if len(buf) >= BATCH_SIZE:
                embs = get_embeddings(buf)
                store.add(embs, metas)
                total_chunks += len(buf)
                buf, metas = [], []

        if buf:
            embs = get_embeddings(buf)
            store.add(embs, metas)
            total_chunks += len(buf)

        files_added += 1

    return {"added": files_added, "chunks": total_chunks}
