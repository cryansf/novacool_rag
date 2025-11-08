from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os, io, zipfile, datetime, re, json, hashlib, collections
from urllib.parse import urljoin, urlparse
import requests
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from docx import Document

# OpenAI modern SDK
from openai import OpenAI
from collections import Counter

# =============================================================================
# CONFIG
# =============================================================================
app = Flask(__name__)
CORS(app)

RENDER = bool(os.getenv("RENDER"))
BASE_DIR = os.getcwd()
UPLOAD_FOLDER = "/data/uploads" if RENDER else os.path.join(BASE_DIR, "uploads")
INDEX_DIR = "/data/index" if RENDER else os.path.join(BASE_DIR, "index")
KB_PATH = "/data/knowledge_base.txt" if RENDER else os.path.join(BASE_DIR, "knowledge_base.txt")
MANIFEST_PATH= "/data/manifest.json" if RENDER else os.path.join(BASE_DIR, "manifest.json")

for p in [UPLOAD_FOLDER, INDEX_DIR, os.path.dirname(KB_PATH)]:
    os.makedirs(p, exist_ok=True)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

# =============================================================================
# MANIFEST (dedup/versioning)
# =============================================================================
def _load_manifest():
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def _save_manifest(entries):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

MANIFEST = _load_manifest()
HASH_INDEX = {e.get("hash"): e for e in MANIFEST if e.get("hash")}

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _manifest_add(entry: dict):
    # For file entries, prefer hash as identity; for pages, prefer URL+type
    h = entry.get("hash")
    if h:
        old = HASH_INDEX.get(h)
        if old:
            return False # exact duplicate
        MANIFEST.append(entry)
        HASH_INDEX[h] = entry
    else:
        # page entry (no hash), dedupe on source + type
        for e in MANIFEST:
            if e.get("source") == entry.get("source") and e.get("type") == entry.get("type"):
                # update in place (new timestamp/chunk count)
                e.update(entry)
                _save_manifest(MANIFEST)
                return True
        MANIFEST.append(entry)
    _save_manifest(MANIFEST)
    return True

# =============================================================================
# TEXT PIPELINE (extract → chunk → index → retrieve)
# =============================================================================
def read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def write_text_file(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def extract_text_from_pdf(path: str) -> str:
    out = []
    try:
        reader = PdfReader(path)
        for p in reader.pages:
            out.append(p.extract_text() or "")
    except Exception as e:
        print(f"PDF extract error ({path}): {e}")
    return "\n".join(out).strip()

def extract_text_from_docx(path: str) -> str:
    out = []
    try:
        doc = Document(path)
        for para in doc.paragraphs:
            out.append(para.text)
    except Exception as e:
        print(f"DOCX extract error ({path}): {e}")
    return "\n".join(out).strip()

def clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def chunk_text(text: str, chunk_size=1200, overlap=200):
    text = clean_spaces(text)
    if not text:
        return []
    chunks = []
    start, L = 0, len(text)
    while start < L:
        end = min(L, start + chunk_size)
        chunks.append(text[start:end])
        if end == L: break
        start = max(0, end - overlap)
    return chunks

def index_text(source_name: str, full_text: str) -> int:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", source_name)[:120]
    chunks = chunk_text(full_text)
    count = 0
    for i, ch in enumerate(chunks, 1):
        out_path = os.path.join(INDEX_DIR, f"{safe}_chunk{i:03d}.txt")
        write_text_file(out_path, ch)
        count += 1
    # Append to knowledge base archive
    kb_line = f"\n\n===== {source_name} ({datetime.datetime.now().isoformat()}) =====\n{full_text}\n"
    with open(KB_PATH, "a", encoding="utf-8") as kb:
        kb.write(kb_line)
    return count

def index_file(filepath: str) -> int:
    name = os.path.basename(filepath)
    text = ""
    lower = name.lower()
    if lower.endswith(".pdf"):
        text = extract_text_from_pdf(filepath)
    elif lower.endswith(".docx"):
        text = extract_text_from_docx(filepath)
    elif lower.endswith(".txt"):
        text = read_text_file(filepath)
    else:
        print(f"Skipping unsupported file type: {name}")
        return 0

    if not text.strip():
        print(f"Empty/unreadable: {name}")
        return 0
    chunks = index_text(name, text)
    print(f"Indexed {name} → {chunks} chunk(s)")
    return chunks

def tokenize(s: str):
    return re.findall(r"[a-zA-Z0-9]+", s.lower())

def score_overlap(qt, dt):
    q = Counter(qt)
    d = Counter(dt)
    return sum(min(q[t], d[t]) for t in q)

def retrieve_context(query: str, k=6, max_chars=8000) -> str:
    q_tokens = tokenize(query)
    cands = []
    for fname in os.listdir(INDEX_DIR):
        if not fname.endswith(".txt"): continue
        path = os.path.join(INDEX_DIR, fname)
        txt = read_text_file(path)
        if not txt: continue
        sc = score_overlap(q_tokens, tokenize(txt))
        if sc > 0:
            cands.append((sc, txt))
    cands.sort(key=lambda x: x[0], reverse=True)
    out, total = [], 0
    for _, txt in cands[: max(10, k*2)]:
        if total >= max_chars: break
        out.append(txt); total += len(txt)
        if len(out) >= k: break
    return "\n\n".join(out)

# =============================================================================
# UTIL: URL / PAGE HELPERS
# =============================================================================
def is_internal_link(base_url: str, link_url: str) -> bool:
    try:
        base = urlparse(base_url)
        link = urlparse(link_url)
        return link.netloc == "" or link.netloc == base.netloc
    except Exception:
        return False

def normalize_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href)

def save_page_text_to_uploads(url: str, text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", urlparse(url).path.strip("/")) or "home"
    name = f"page_{urlparse(url).netloc.replace('.', '_')}_{slug}.txt"
    path = os.path.join(UPLOAD_FOLDER, name)
    write_text_file(path, text)
    return path

# =============================================================================
# ROUTES: UI
# =============================================================================
@app.route("/")
def index():
    return "<h2>Novacool RAG Deployment Active</h2><p>Visit /uploader, /chat, or /widget</p>"

@app.route("/uploader")
def uploader_page():
    return render_template("uploader.html")

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/widget")
def widget_page():
    return render_template("widget.html")

@app.route("/admin/uploader")
def admin_uploader_alias():
    return render_template("uploader.html")

# =============================================================================
# ROUTES: UPLOAD (dedupe + index)
# =============================================================================
@app.route("/upload", methods=["POST"])
def upload_files():
    if "files" not in request.files:
        return jsonify({"status": "No files found in request"}), 400

    files = request.files.getlist("files")
    saved, indexed, skipped = 0, 0, 0

    for f in files:
        if not f.filename:
            continue
        filename = secure_filename(f.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        # read bytes for hash without storing twice
        data = f.read()
        f.seek(0)
        file_hash = _sha256_bytes(data)

        if file_hash in HASH_INDEX:
            print(f"Duplicate upload skipped: {filename}")
            skipped += 1
            continue

        f.save(save_path)
        saved += 1

        # index & manifest
        chunks = index_file(save_path)
        entry = {
            "source": filename,
            "filename": filename,
            "type": os.path.splitext(filename)[1].lstrip(".").lower(),
            "chunks": chunks,
            "indexed_on": datetime.datetime.now().isoformat(),
            "hash": file_hash,
            "size_kb": round(len(data) / 1024, 2)
        }
        _manifest_add(entry)

    return jsonify({"status": f"Uploaded {saved}, skipped {skipped} duplicates, indexed {saved - skipped}."})

# =============================================================================
# ROUTES: REINDEX (clean + rebuild)
# =============================================================================
@app.route("/reindex", methods=["POST"])
def reindex_all():
    try:
        # clear index + kb
        for n in os.listdir(INDEX_DIR):
            try: os.remove(os.path.join(INDEX_DIR, n))
            except: pass
        try:
            if os.path.exists(KB_PATH): os.remove(KB_PATH)
        except: pass

        indexed_files = 0
        for fname in os.listdir(UPLOAD_FOLDER):
            if fname.lower().endswith((".pdf", ".docx", ".txt")):
                fpath = os.path.join(UPLOAD_FOLDER, fname)
                if index_file(fpath) > 0:
                    indexed_files += 1

        return jsonify({"status": f"Reindexed {indexed_files} document(s) successfully."})
    except Exception as e:
        print("Reindex error:", e)
        return jsonify({"status": f"Reindex failed: {e}"}), 500

# =============================================================================
# ROUTES: MANIFEST VIEW
# =============================================================================
@app.route("/manifest", methods=["GET"])
def manifest_view():
    return jsonify(MANIFEST)

# =============================================================================
# ROUTES: CRAWL (recursive, ingest docs, index all)
# =============================================================================
@app.route("/crawl", methods=["POST"])
def crawl_site():
    """
    JSON body:
      { "url": "<start_url>", "depth": 1, "max_pages": 25 }
    - Crawls page(s) up to 'depth' (internal links only)
    - Extracts readable text (saves a page .txt into uploads)
    - Finds and downloads .pdf/.docx → indexes automatically
    - Updates manifest with hashes to avoid duplicates
    """
    try:
        data = request.get_json(force=True)
        start_url = (data.get("url") or "").strip()
        depth = int(data.get("depth") or 1)
        max_pages = int(data.get("max_pages") or 25)

        if not start_url:
            return jsonify({"status": "No URL provided"}), 400

        visited = set()
        q = collections.deque()
        q.append((start_url, 0))

        pages_crawled = 0
        page_text_chunks = 0
        downloaded, indexed_docs, skipped_dupes = [], [], []

        while q and pages_crawled < max_pages:
            url, d = q.popleft()
            if url in visited:
                continue
            visited.add(url)

            print(f"🌐 Fetching: {url} (depth {d})")
            try:
                r = requests.get(url, timeout=20)
            except Exception as e:
                print(f"Fetch failed: {url} → {e}")
                continue

            if r.status_code != 200 or not r.text:
                print(f"Non-200 or empty: {url}")
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]): tag.decompose()
            page_text = clean_spaces(soup.get_text(" ", strip=True))

            # Save page text to uploads and index
            if page_text:
                page_txt_path = save_page_text_to_uploads(url, page_text)
                chunks = index_text(os.path.basename(page_txt_path), page_text)
                page_text_chunks += chunks
                # add page entry (no hash)
                _manifest_add({
                    "source": url,
                    "filename": os.path.basename(page_txt_path),
                    "type": "page",
                    "chunks": chunks,
                    "indexed_on": datetime.datetime.now().isoformat(),
                    "size_kb": round(len(page_text.encode("utf-8"))/1024, 2)
                })

            # Find linked docs and download/index
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href:
                    continue
                # documents
                if any(href.lower().endswith(ext) for ext in [".pdf", ".docx"]):
                    file_url = normalize_url(url, href)
                    filename = os.path.basename(urlparse(file_url).path)
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    try:
                        rr = requests.get(file_url, timeout=25)
                        if rr.status_code == 200 and rr.content:
                            file_hash = _sha256_bytes(rr.content)
                            if file_hash in HASH_INDEX:
                                print(f"Duplicate (skip): {filename}")
                                skipped_dupes.append(filename)
                                continue
                            with open(save_path, "wb") as f:
                                f.write(rr.content)
                            downloaded.append(filename)
                            chunks = index_file(save_path)
                            if chunks > 0:
                                indexed_docs.append(filename)
                            _manifest_add({
                                "source": file_url,
                                "filename": filename,
                                "type": os.path.splitext(filename)[1].lstrip(".").lower(),
                                "chunks": chunks,
                                "indexed_on": datetime.datetime.now().isoformat(),
                                "hash": file_hash,
                                "size_kb": round(len(rr.content)/1024, 2)
                            })
                    except Exception as e:
                        print(f"Download/index failed: {file_url} → {e}")

                # enqueue child page if internal and depth allows
                elif d < depth:
                    child = normalize_url(url, href)
                    if is_internal_link(url, child) and child not in visited:
                        q.append((child, d+1))

            pages_crawled += 1

        return jsonify({
            "status": "Crawl complete",
            "pages_crawled": pages_crawled,
            "page_text_chunks": page_text_chunks,
            "files_downloaded": downloaded,
            "files_indexed": indexed_docs,
            "duplicates_skipped": skipped_dupes
        })

    except Exception as e:
        print("Crawl error:", e)
        return jsonify({"status": f"Crawl failed: {e}"}), 500

# =============================================================================
# ROUTES: CHAT (RAG)
# =============================================================================
@app.route("/api/chat", methods=["POST"])
def chat_api():
    try:
        data = request.get_json(force=True)
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        context = retrieve_context(user_message, k=6, max_chars=8000)
        system_prompt = (
            "You are the Novacool AI Assistant. Use ONLY the supplied context where possible. "
            "If the answer is not in context, say you don't have it yet. Be precise and cite facts plainly.\n\n"
            f"Context:\n{context if context else '[No indexed context found yet]'}"
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,
            max_tokens=450
        )
        reply = resp.choices[0].message.content.strip()
        return jsonify({"reply": reply})
    except Exception as e:
        print("Chat API error:", e)
        return jsonify({"error": str(e)}), 500

# =============================================================================
# ROUTES: BACKUP (ZIP everything needed to restore)
# =============================================================================
@app.route("/backup", methods=["GET"])
def generate_backup():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    zip_name = f"novacool_backup_{timestamp}.zip"

    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as zf:
        include = [
            "app_flask.py",
            "templates",
            "static",
            "requirements.txt",
            UPLOAD_FOLDER,
            INDEX_DIR,
            KB_PATH,
            MANIFEST_PATH
        ]
        for item in include:
            if not item: continue
            if os.path.isdir(item):
                for root, _, files in os.walk(item):
                    for f in files:
                        p = os.path.join(root, f)
                        arc = os.path.relpath(p, start=BASE_DIR)
                        zf.write(p, arc)
            elif os.path.isfile(item):
                arc = os.path.relpath(item, start=BASE_DIR)
                zf.write(item, arc)

    memory.seek(0)
    return send_file(memory, as_attachment=True, download_name=zip_name, mimetype="application/zip")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

