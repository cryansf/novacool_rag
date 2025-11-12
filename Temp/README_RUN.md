# Novacool RAG — Memory-Safe Build (Persistent /data)

## Run Locally
```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...   # set in your shell or .env
python app_flask.py
```
Visit http://localhost:8000, upload a PDF/DOCX/TXT, then ask a question.

## Render Notes
- Ensure a **Persistent Disk** mounted at `/data` (2–5 GB+ recommended).
- Environment variables:
  - `OPENAI_API_KEY`
  - Optional: `CHUNK_TOKENS`, `CHUNK_OVERLAP`, `TOP_K`, `DATA_ROOT=/data`
- Start command: `gunicorn app_flask:app`
- This build includes:
  - `MAX_CONTENT_LENGTH = 25 MB` to prevent huge uploads
  - Streaming embeddings in batches of 40 chunks to limit RAM
  - `text-embedding-3-small` (1536-dim) for lower memory

## API
- `POST /upload` — form-data: `files` (multiple). Returns `saved`, `added`, `chunks`.
- `POST /reindex` — re-embeds everything currently in `/data/uploads`.
- `POST /chat` — JSON `{ "message": str, "top_k"?: int }` → `{ answer, sources }`.
- `GET /health` — readiness probe.
