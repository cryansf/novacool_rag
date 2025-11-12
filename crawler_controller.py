# crawler_engine.py
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from rag_pipeline import ingest_text

UPLOAD_DIR = "/data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def fetch_links(base_url):
    """Scrape a webpage and return all linked PDF/DOCX URLs."""
    try:
        res = requests.get(base_url, timeout=15)
        res.raise_for_status()
    except Exception as e:
        return [], f"❌ Failed to fetch {base_url}: {e}"

    soup = BeautifulSoup(res.text, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        if full_url.lower().endswith((".pdf", ".docx")):
            links.append(full_url)

    return links, f"✅ Found {len(links)} linked documents on {base_url}"

def download_file(url):
    """Download a linked file into /data/uploads and return its path."""
    try:
        filename = os.path.basename(urlparse(url).path)
        if not filename:
            filename = "unnamed_file"
        filepath = os.path.join(UPLOAD_DIR, filename)

        with requests.get(url, stream=True, timeout=20) as r:
            r.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return filepath, f"📄 Downloaded {filename}"
    except Exception as e:
        return None, f"⚠️ Failed to download {url}: {e}"

def crawl_and_ingest(base_url):
    """Main autonomous crawling + ingestion pipeline."""
    links, summary = fetch_links(base_url)
    logs = [summary]

    for link in links:
        file_path, msg = download_file(link)
        logs.append(msg)
        if file_path:
            result = ingest_text(file_path)
            logs.append(f"🧠 {result}")

    if not links:
        logs.append("No documents found to ingest.")
    return logs
