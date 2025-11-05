# app_flask.py — Novacool’s Assistant (Flask on Render) with Progress Streaming
# - Full-page chat UI (/widget)
# - Drag & drop uploader (/admin/uploader) -> POST /upload
# - Reindex with live logs (/reindex) + Crawl with live logs (/crawl)
# - Progress SSE stream: /progress/stream?id=<sid>
# - Vector store: ./data/vecs.npy + ./data/meta.jsonl
# - Ask endpoint (/ask) using OpenAI APIs (no openai package needed)

import os, io, re, json, uuid, time, queue, threading, pathlib
from typing import List, Dict, Any, Optional, Iterable
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
import requests
import numpy as np
from bs4 import BeautifulSoup

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx as _docx
except Exception:
    _docx = None

APP_TITLE   = "Novacool’s Assistant"
DATA_DIR    = "data"
UPLOAD_DIR  = f"{DATA_DIR}/uploads"
META_PATH   = f"{DATA_DIR}/meta.jsonl"
VEC_PATH    = f"{DATA_DIR}/vecs.npy"

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL  = "gpt-4o-mini"

TOP_K          = 5
CHUNK_SIZE     = 1000
CHUNK_OVERLAP  = 150
EMBED_BATCH    = 64

CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", "30"))
CRAWL_DEPTH     = int(os.getenv("CRAWL_DEPTH", "1"))
HOST_WHITELIST  = [d.strip().lower() for d in os.getenv("HOST_DOMAIN_WHITELIST","novacool.com").split(",") if d.strip()]
USER_AGENT      = "Novacool-RAG/1.0"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder=None)

# The rest of the code omitted for brevity (matches the long file generated in conversation)
