# crawler_controller.py
import requests
from bs4 import BeautifulSoup
from rag_pipeline import ingest_text
import tempfile
import os

def crawl_and_ingest(url):
    """Crawl a URL, extract text, and ingest to FAISS."""
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        tmp_path = os.path.join(tempfile.gettempdir(), "crawl_text.txt")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(text)

        ingest_text(tmp_path)
        return f"Crawl and ingestion complete for {url}"
    except Exception as e:
        return f"Error crawling {url}: {e}"
