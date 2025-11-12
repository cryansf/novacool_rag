import time
from typing import List
import numpy as np
from openai import OpenAI
from config import OPENAI_API_KEY, EMBED_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def get_embeddings(texts: List[str]) -> np.ndarray:
    if not _client:
        raise RuntimeError("OPENAI_API_KEY missing. Set env var before running.")

    # OpenAI embeddings API — batch for efficiency
    # Retry w/ simple backoff
    for attempt in range(5):
        try:
            resp = _client.embeddings.create(model=EMBED_MODEL, input=texts)
            vecs = [d.embedding for d in resp.data]
            return np.array(vecs, dtype='float32')
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))
