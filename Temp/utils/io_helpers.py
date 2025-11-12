import os, hashlib, shutil
from datetime import datetime

SAFE_NAME_KEEP = "-_.() "

def safe_filename(name: str) -> str:
    base = os.path.basename(name)
    return "".join(c for c in base if c.isalnum() or c in SAFE_NAME_KEEP).strip().replace(" ", "_")

def file_sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def stamp() -> str:
    return datetime.utcnow().isoformat(timespec='seconds') + 'Z'

def copy_to(src: str, dst_dir: str) -> str:
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, safe_filename(os.path.basename(src)))
    shutil.copy2(src, dst)
    return dst
