from typing import List, Dict
import tiktoken

# Token-aware chunking for gpt-4* encodings.
_enc = tiktoken.get_encoding("cl100k_base")

def chunk_text(text: str, chunk_tokens: int = 500, overlap: int = 80) -> List[Dict]:
    tokens = _enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_tokens, len(tokens))
        piece = _enc.decode(tokens[start:end])
        chunks.append({"text": piece})
        if end == len(tokens):
            break
        start = max(0, end - overlap)
    return chunks
