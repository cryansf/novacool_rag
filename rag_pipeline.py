"""
Lightweight RAG ingestion and search pipeline placeholder.
Ensures backend starts even if no vector database is configured yet.
"""

def ingest_text(text, source=None):
    """
    Placeholder ingestion function.
    In a full RAG pipeline, this would embed text and store vectors.
    """
    print(f"[RAG] Ingested {len(text)} characters from {source or 'uploaded data'}.")


def search_docs(query):
    """
    Placeholder retrieval function.
    In a real implementation, this would perform a vector search.
    """
    print(f"[RAG] Searching docs for: {query}")
    return [{"text": "This is placeholder context until RAG indexing is live."}]
