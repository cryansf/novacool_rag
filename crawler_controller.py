import os
import threading
import time
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from flask import current_app, jsonify, request

# We no longer import from app_flask here to avoid circular import


class CrawlerManager:
    def __init__(self):
        self.active = False
        self.paused = False
        self.stopped = False
        self.progress = 0
        self.status = "Idle"
        self.thread = None
        self.data_dir = "/opt/render/project/data"
        self.manifest_path = os.path.join(self.data_dir, "manifest.json")
        self.knowledge_base_path = os.path.join(self.data_dir, "knowledge_base.txt")
        os.makedirs(self.data_dir, exist_ok=True)

    # ---------------------------------------------------------------------
    # Core control methods
    # ---------------------------------------------------------------------
    def start(self, base_url):
        """Start a background crawling thread."""
        if self.active:
            raise RuntimeError("Crawler already running")

        self.active = True
        self.paused = False
        self.stopped = False
        self.progress = 0
        self.status = "Starting crawl..."
        self.thread = threading.Thread(target=self._crawl_site, args=(base_url,))
        self.thread.daemon = True
        self.thread.start()

    def pause(self):
        """Toggle pause state."""
        if not self.active:
            return
        self.paused = not self.paused
        self.status = "Paused" if self.paused else "Resumed"

    def stop(self):
        """Stop the crawler completely."""
        self.stopped = True
        self.status = "Stopped"

    # ---------------------------------------------------------------------
    # Internal crawling logic
    # ---------------------------------------------------------------------
    def _crawl_site(self, base_url):
        """Perform a simple web crawl and store text content."""
        try:
            self.status = "Crawling"
            visited = set()
            to_visit = [base_url]
            pages = []

            while to_visit and not self.stopped:
                if self.paused:
                    time.sleep(1)
                    continue

                url = to_visit.pop(0)
                if url in visited:
                    continue
                visited.add(url)

                try:
                    response = requests.get(url, timeout=10)
                    if "text/html" not in response.headers.get("Content-Type", ""):
                        continue

                    soup = BeautifulSoup(response.text, "html.parser")
                    text = soup.get_text(separator=" ", strip=True)

                    # Save content to knowledge base file
                    with open(self.knowledge_base_path, "a", encoding="utf-8") as kb:
                        kb.write(f"\n\n# {url}\n{text}\n")

                    pages.append(url)
                    self.progress = int((len(visited) / 50) * 100)

                    # Discover internal links
                    for a in soup.find_all("a", href=True):
                        href = urljoin(url, a["href"])
                        if base_url in href and href not in visited:
                            to_visit.append(href)

                except Exception as e:
                    print(f"[Crawler] Error fetching {url}: {e}")
                    continue

                time.sleep(0.5)

            # --- When finished ---
            self.status = f"Crawl finished. {len(pages)} pages added."
            self.active = False
            self.progress = min(100, self.progress)

            # Reindex safely inside app context (no circular import)
            from app_flask import reindex_knowledge_base
            with current_app.app_context():
                try:
                    reindex_knowledge_base()
                    self.status += " Reindex complete."
                except Exception as e:
                    self.status += f" (Reindex skipped: {e})"

        except Exception as e:
            self.status = f"Error: {e}"
            self.active = False
        finally:
            self.active = False


# ---------------------------------------------------------------------
# Route registration helper
# ---------------------------------------------------------------------
def register_crawler_routes(app, crawler):
    """Register API routes for controlling the crawler."""
    @app.route("/start_crawl", methods=["POST"])
    def start_crawl_route():
        data = request.get_json()
        url = data.get("url")
        if not url:
            return jsonify({"error": "Missing base URL"}), 400
        try:
            crawler.start(url)
            return jsonify({"message": f"Crawl started for {url}"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/pause_crawl", methods=["GET"])
    def pause_crawl_route():
        crawler.pause()
        return jsonify({"message": "Crawler paused/resumed"}), 200

    @app.route("/stop_crawl", methods=["GET"])
    def stop_crawl_route():
        crawler.stop()
        return jsonify({"message": "Crawler stopped"}), 200
