# app_flask.py — Novacool’s Assistant (Flask on Render)
# - Full-page chat UI (/widget)
# - Drag & drop uploader (/admin/uploader)
# - Reindex to rebuild embeddings (/reindex)
# - Crawl Novacool.com and embed web content (/crawl)
# - Ask endpoint for OpenAI RAG queries
# - Vector store: ./data/vecs.npy + ./data/meta.jsonl

import os, io, re, json, time, uuid, pathlib, urllib.parse, queue
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify, Response, render_template, send_from_directory
import requests
import numpy as np
from bs4 import BeautifulSoup

# ---------- Config ----------
APP_TITLE = "Novacool’s Assistant"
DATA_DIR = "data"
UPLOAD_DIR = f"{DATA_DIR}/uploads"
META_PATH = f"{DATA_DIR}/meta.jsonl"
VEC_PATH  = f"{DATA_DIR}/vecs.npy"

EMBED_MODEL = "text-embedding-3-small"   # 1536 dims
CHAT_MODEL  = "gpt-4o-mini"
TOP_K = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
CRAWL_LIMIT = 10   # maximum number of pages to crawl

HOST_WHITELIST = [d.strip().lower() for d in os.getenv("HOST_DOMAIN_WHITELIST","novacool.com").split(",") if d.strip()]
USER_AGENT = "Novacool-RAG/1.0"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name
