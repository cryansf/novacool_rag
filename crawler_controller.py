# crawler_controller.py
import os
import re
import time
import threading
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from flask import Blueprint, request, jsonify

# Optional PDF parser
from io import BytesIO
from PyPDF2 import PdfReader

# --- Configuration ---
DATA_DIR = "data"
KB_PATH = os.path.join(DATA_DIR, "knowledge_base.txt")

# --- Crawler Manager ---
class CrawlerManager:
    def __init__(self):
        self.reset()

    def reset(self):
        self.active = False
        self.paused = False
        self.stopped = False
        self.progress = 0
        self.status = "Idle"
        self.done = False
        self.total_links = 0
        self.crawled_links = 0
        self.thread = None

    def start(self, base_url):
        if self.active:
            return "Crawl already running."
        self.reset()
        self.active = True
        self.status = f"Starting crawl for {base_url}"
        self.thread = threading.Thread(target=self._crawl_task, args=(base_url,), daemon=True)
        self.thread.start()
        return "Crawl started."

    def _crawl_task(self, base_url):
        try:
            visited = set()
            queue = [base_url]
            all_texts = []

            domain = urlparse(base_url).netloc
            self.total_links = 1

            while queue and not self.stopped:
                if self.paused:
                    self.status = "⏸️ Paused..."
                    time.sleep(1)
                    continue

                url = queue.pop(0)
                if url in visited:
                    continue
                visited.add(url)
                self.crawled_links += 1
                self.progress = int((self.crawled_links / max(self.total_links, 1)) * 100)
                self.status = f"Crawling {url} ({self.crawled_links}/{self.total_links})"

                try:
                    resp = requests.get(url, timeout=10, headers={"User-Agent": "NovacoolCrawler/1.0"})
                    content_type = resp.headers.get("Content-Type", "").lower()

                    text = ""
                    if "text/html" in content_type:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        text = soup.get_text(separator=" ", strip=True)
                        # Find and queue new links
                        for a in soup.find_all("a", href=True):
                            new_url = urljoin(url, a["href"])
                            if urlparse(new_url).netloc == domain and new_url not in visited:
                                queue.append(new_url)
                                self.total_links += 1

                    elif "application/pdf" in content_type:
                        reader = PdfReader(BytesIO(resp.content))
                        for page in reader.pages:
                            text += page.extract_text() or ""

                    if text.strip():
                        clean_text = re.sub(r"\s+", " ", text)
                        all_texts.append(f"URL: {url}\n{clean_text}\n\n")

                except Exception as e:
                    self.status = f"⚠️ Error fetching {url}: {e}"

                # Throttle slightly to avoid hammering
                time.sleep(0.5)

                # Progress update
                self.progress = min(100, int((self.crawled_links / max(self.total_links, 1)) * 100))

            # --- Save collected text ---
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR, exist_ok=True)
            with open(KB_PATH, "a", encoding="utf-8") as f:
                for block in all_texts:
                    f.write(block)

            self.status = f"✅ Crawl finished. {len(visited)} pages added."
            self.active = False
            self.done = True

            # Trigger reindex automatically if available
            try:
                from app_flask import reindex_knowledge_base
                reindex_knowledge_base()
                self.status += " Reindex complete."
            except Exception as e:
                self.status += f" (Reindex skipped: {e})"

        except Exception as e:
            self.status = f"❌ Fatal error: {e}"
            self.active = False
            self.done = True

    def pause(self):
        if self.active:
            self.paused = not self.paused
            self.status = "Paused" if self.paused else "Resumed"
            return True
        return False

    def stop(self):
        if self.active:
            self.stopped = True
            self.status = "Stopped by user"
            return True
        return False


# --- Register Routes ---
def register_crawler_routes(app, crawler):
    bp = Blueprint("crawler_bp", __name__)

    @bp.route("/crawl", methods=["POST"])
    def start_crawl():
        data = request.get_json()
        base_url = data.get("url", "")
        msg = crawler.start(base_url)
        return jsonify({"status": msg})

    @bp.route("/pause_crawl", methods=["POST"])
    def pause_crawl():
        crawler.pause()
        return jsonify({"status": crawler.status})

    @bp.route("/stop_crawl", methods=["POST"])
    def stop_crawl():
        crawler.stop()
        return jsonify({"status": "Stopped"})

    @bp.route("/crawl_status")
    def crawl_status():
        return jsonify({
            "percent": crawler.progress,
            "message": crawler.status,
            "complete": crawler.done,
            "stopped": crawler.stopped
        })

    app.register_blueprint(bp)
