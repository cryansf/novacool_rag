import os
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from rag_pipeline import ingest_text

DATA_DIR = Path("data/index")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def crawl_and_ingest(url: str):
    """Fetch text from a webpage and store it for retrieval."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        text = " ".join([t.get_text(strip=True) for t in soup.find_all(["p", "li", "h1", "h2", "h3"])])
        
        file_path = DATA_DIR / f"{url.replace('https://','').replace('/','_')}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        ingest_text(text, url)
        return f"Ingested {len(text)} characters from {url}"

    except Exception as e:
        return f"Failed to crawl {url}: {e}"
