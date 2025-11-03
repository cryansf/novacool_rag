# Lightweight RAG chatbot for cPanel/WSGI (Flask)
# - Uses OpenAI embeddings (no PyTorch, no faiss)
# - Stores vectors as .npy + JSONL under ./data
# - Endpoints: /ask, /ingest/files, /ingest/urls, /widget

import os, io, re, json, time, uuid, pathlib, queue, urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from flask import Flask, request, jsonify, Response
import requests
from bs4 import BeautifulSoup
import numpy as np

# ------- Config -------
APP_TITLE = "Novacool Chat (cPanel)"
DATA_DIR = "./data"
MANIFEST = f"{DATA_DIR}/manifest.json"
META_PATH = f"{DATA_DIR}/meta.jsonl"
VEC_PATH = f"{DATA_DIR}/vecs.npy"   # NxD float32 matrix
EMBED_MODEL = "text-embedding-3-small"   # 1536 dims
TOP_K = 5
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", "30"))
CRAWL_DEPTH = int(os.getenv("CRAWL_DEPTH", "1"))
USER_AGENT = "Novacool-RAG-cPanel/1.0"
HOST_DOMAIN_WHITELIST = [d.strip().lower() for d in os.getenv("HOST_DOMAIN_WHITELIST","novacool.com").split(",") if d.strip()]

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None
try:
    import docx
except Exception:
    docx = None

app = Flask(__name__)
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(MANIFEST):
    with open(MANIFEST, "w") as f:
        json.dump({"embedding_model": EMBED_MODEL, "created": time.time()}, f)

# ------- Helpers -------
def normspace(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> List[str]:
    text = normspace(text)
    if not text: return []
    out, start = [], 0
    L = len(text)
    while start < L:
        end = min(L, start + size)
        out.append(text[start:end])
        if end == L: break
        start = max(0, end - overlap)
    return out

def canonicalize_url(base_or_url: str, link: str = "") -> Optional[str]:
    try:
        u = urllib.parse.urljoin(base_or_url, link) if link else base_or_url
        parsed = urllib.parse.urlparse(u)
        if not parsed.scheme.startswith("http"): return None
        clean = parsed._replace(fragment="", query="").geturl()
        return clean
    except Exception:
        return None

def hostname(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""

def same_domain_allowed(url: str) -> bool:
    h = hostname(url)
    return any(h.endswith(w) for w in HOST_DOMAIN_WHITELIST)

# ------- Storage -------
def load_meta() -> List[Dict[str,Any]]:
    if not os.path.exists(META_PATH): return []
    with open(META_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]

def save_meta(metas: List[Dict[str,Any]]):
    with open(META_PATH, "w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

def load_vecs() -> np.ndarray:
    if not os.path.exists(VEC_PATH):
        return np.zeros((0, 1536), dtype=np.float32)
    return np.load(VEC_PATH)

def save_vecs(arr: np.ndarray):
    np.save(VEC_PATH, arr)

# ------- Embeddings (OpenAI) -------
def openai_embeddings(texts: List[str]) -> np.ndarray:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    # Single batched request (rate limits are generous for small batches)
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {"input": texts, "model": EMBED_MODEL}
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    vecs = [d["embedding"] for d in r.json()["data"]]
    arr = np.array(vecs, dtype=np.float32)
    # Normalize for cosine via dot product
    norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return (arr / norms).astype(np.float32)

# ------- Parsing -------
def parse_pdf(b: bytes, fname: str) -> List[Dict[str,Any]]:
    if PdfReader is None:
        raise RuntimeError("PDF support missing (pypdf not installed)")
    reader = PdfReader(io.BytesIO(b))
    out = []
    for i, page in enumerate(reader.pages):
        try:
            txt = normspace(page.extract_text() or "")
        except Exception:
            txt = ""
        for c in chunk_text(txt):
            out.append({"source_type":"pdf","source":fname,"location":f"p. {i+1}","text":c})
    return out

def parse_docx(b: bytes, fname: str) -> List[Dict[str,Any]]:
    if docx is None:
        raise RuntimeError("DOCX support missing (python-docx not installed)")
    d = docx.Document(io.BytesIO(b))
    body = "\n".join([normspace(p.text) for p in d.paragraphs if normspace(p.text)])
    return [{"source_type":"docx","source":fname,"location":"N/A","text":c} for c in chunk_text(body)]

def parse_text(b: bytes, fname: str) -> List[Dict[str,Any]]:
    try:
        body = b.decode("utf-8")
    except Exception:
        body = b.decode("latin-1", errors="ignore")
    return [{"source_type":"text","source":fname,"location":"N/A","text":c} for c in chunk_text(body)]

def fetch_html(url: str, timeout=15) -> Optional[str]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        if r.status_code == 200 and "text/html" in r.headers.get("content-type",""):
            return r.text
        return None
    except Exception:
        return None

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script","style","noscript"]): t.decompose()
    return normspace(soup.get_text(separator=" "))

def crawl(start_url: str, max_pages=CRAWL_MAX_PAGES, depth=CRAWL_DEPTH) -> Dict[str,str]:
    root = canonicalize_url(start_url) or ""
    if not root: return {}
    if not same_domain_allowed(root):
        raise RuntimeError(f"URL domain not allowed: {HOST_DOMAIN_WHITELIST}")
    seen, pages = set(), {}
    q = queue.Queue()
    q.put((root, 0))
    while not q.empty() and len(pages) < max_pages:
        url, d = q.get()
        if url in seen: continue
        seen.add(url)
        html = fetch_html(url)
        if not html: continue
        pages[url] = html
        if d >= depth: continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            nxt = canonicalize_url(url, a["href"])
            if not nxt: continue
            if hostname(nxt).endswith(hostname(root)) and nxt not in seen and len(pages)+q.qsize() < max_pages:
                q.put((nxt, d+1))
    return pages

# ------- Index ops -------
def add_chunks(chunks: List[Dict[str,Any]]) -> int:
    if not chunks: return 0
    texts = [c["text"] for c in chunks]
    vecs_new = openai_embeddings(texts)  # (n,1536) normalized
    vecs_old = load_vecs()
    vecs = vecs_new if vecs_old.shape[0]==0 else np.vstack([vecs_old, vecs_new])
    save_vecs(vecs)

    metas = load_meta()
    for c in chunks:
        c["id"] = str(uuid.uuid4())
    metas.extend(chunks)
    save_meta(metas)
    return len(chunks)

def search(query: str, k=TOP_K) -> List[Dict[str,Any]]:
    vecs = load_vecs()
    metas = load_meta()
    if vecs.shape[0] == 0:
        return []
    qv = openai_embeddings([query])[0:1]  # (1,D)
    sims = (vecs @ qv.T).reshape(-1)      # cosine via dot product (all normalized)
    top_idx = np.argsort(-sims)[:min(k, vecs.shape[0])]
    out = []
    for i in top_idx:
        m = metas[i].copy()
        m["_score"] = float(sims[i])
        out.append(m)
    return out

def call_llm(question: str, ctx_blocks: List[str], cites: List[str]) -> str:
    key = os.getenv("OPENAI_API_KEY","").strip()
    if not key:
        # Basic extractive fallback
        stitched = "\n\n".join(f"- {c[:500]}..." for c in ctx_blocks)
        return f"(No LLM key set)\n\n{stitched}\n\nSources: " + "; ".join(cites)

    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    prompt = (
        "You are a helpful assistant. Answer ONLY from the provided context. "
        "If the answer is not there, say you don't know. Keep it concise. "
        "Always add a 'Sources:' list.\n\n"
        f"Question: {question}\n\n"
        "Context:\n" + "\n\n".join(ctx_blocks) + "\n\nAnswer:"
    )
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role":"system","content":"Be precise; cite sources; no hallucinations."},
            {"role":"user","content": prompt}
        ],
        "temperature": 0.2
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    ans = r.json()["choices"][0]["message"]["content"].strip()
    if "Sources:" not in ans:
        ans += "\n\nSources: " + "; ".join(cites)
    return ans

WIDGET_HTML = """
<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Novacool Chat</title>
<style>
:root{--bg:#0b1220;--card:#111a2b;--accent:#36c;--text:#e7eefc}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu;background:transparent}
.card{display:flex;flex-direction:column;height:100vh;background:var(--card);color:var(--text)}
header{padding:12px 16px;border-bottom:1px solid #1f2a44;font-weight:600}
#log{flex:1;overflow:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.msg{padding:10px 12px;border-radius:12px;max-width:80%;line-height:1.4}
.you{background:#233154;align-self:flex-end}.bot{background:#162036;align-self:flex-start;white-space:pre-wrap}
form{display:flex;gap:8px;padding:12px;border-top:1px solid #1f2a44}
input[type=text]{flex:1;padding:10px 12px;border-radius:10px;border:1px solid #2a3a63;background:#0e1729;color:var(--text)}
button{padding:10px 14px;border-radius:10px;border:0;background:var(--accent);color:#fff;font-weight:600;cursor:pointer}
.foot{font-size:12px;opacity:.7;padding:0 16px 12px}a{color:#9bc3ff}
</style></head><body>
<div class="card"><header>Novacool Chat</header>
<div id="log"></div>
<form id="chat"><input id="q" type="text" placeholder="Ask about Novacool, mix rates, docs..." autocomplete="off"/><button>Ask</button></form>
<div class="foot">Answers cite PDFs/FAQs and novacool.com pages.</div></div>
<script>
const log=document.getElementById('log'),form=document.getElementById('chat'),q=document.getElementById('q');
function add(role,t){const d=document.createElement('div');d.className='msg '+(role==='you'?'you':'bot');d.textContent=t;log.appendChild(d);log.scrollTop=log.scrollHeight}
form.addEventListener('submit',async(e)=>{e.preventDefault();const query=q.value.trim();if(!query)return;add('you',query);q.value='';
  try{const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:query})});
      const data=await r.json();add('bot',data.answer||'No answer.')}
  catch(err){add('bot','Error: '+err);}});
</script></body></html>
"""

# -------- Routes --------
@app.route("/", methods=["GET"])
def health(): return Response("OK", mimetype="text/plain")

@app.route("/widget", methods=["GET"])
def widget(): return Response(WIDGET_HTML, mimetype="text/html")

@app.route("/ingest/files", methods=["POST"])
def ingest_files():
    if "files" not in request.files: return jsonify({"error":"no files"}), 400
    chunks = []
    for f in request.files.getlist("files"):
        b = f.read()
        ext = pathlib.Path(f.filename).suffix.lower()
        try:
            if ext == ".pdf":
                chunks += parse_pdf(b, f.filename)
            elif ext == ".docx":
                chunks += parse_docx(b, f.filename)
            elif ext in [".txt",".md",".markdown"]:
                chunks += parse_text(b, f.filename)
            else:
                chunks += parse_text(b, f.filename)
        except Exception as e:
            return jsonify({"error": f"Failed {f.filename}: {e}"}), 400
    added = add_chunks(chunks)
    return jsonify({"added_chunks": added})

@app.route("/ingest/urls", methods=["POST"])
def ingest_urls():
    data = request.get_json(force=True, silent=True) or {}
    urls = data.get("urls", [])
    depth = int(data.get("crawl_depth", CRAWL_DEPTH))
    maxp = int(data.get("max_pages", CRAWL_MAX_PAGES))
    pages = {}
    for u in urls:
        u = canonicalize_url(u) or ""
        if not u: continue
        pages.update(crawl(u, max_pages=maxp, depth=depth))
    chunks = []
    for url, html in pages.items():
        txt = html_to_text(html)
        for c in chunk_text(txt):
            chunks.append({"source_type":"web","source":url,"location":"N/A","text":c})
    added = add_chunks(chunks)
    return jsonify({"pages_crawled": len(pages), "added_chunks": added})

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True, silent=True) or {}
    q = (data.get("question") or "").strip()
    if not q: return jsonify({"error":"empty question"}), 400
    ctx = search(q, k=TOP_K)
    blocks, cites = [], []
    for i, c in enumerate(ctx, 1):
        src = f"{c['source']} ({c['location']})" if c.get("location") and c["location"]!="N/A" else c["source"]
        blocks.append(f"[{i}] Source: {src}\n{c['text']}")
        cites.append(f"[{i}] {src}")
    answer = call_llm(q, blocks, cites)
    return jsonify({"answer": answer, "citations": [{"source":c["source"],"location":c.get("location","N/A"),"score":c["_score"]} for c in ctx]})
