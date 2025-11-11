import requests
from bs4 import BeautifulSoup
from rag_pipeline import ingest_text

def crawl_and_ingest(url):
    """
    Crawl a single web page, extract readable text, and ingest it into the RAG vector database.
    This version is independent of Flask (no circular imports).
    """
    print(f"[Crawler] Starting crawl for: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract text and clean it up
        text = soup.get_text(separator='\n', strip=True)

        # Send to your RAG ingestion pipeline
        ingest_text(text)

        print(f"[Crawler] Successfully crawled and ingested: {url}")
    except Exception as e:
        print(f"[Crawler] Error while crawling {url}: {e}")
