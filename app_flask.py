import os, json, time, numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from openai import OpenAI
from tqdm import tqdm

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = "/data/uploads"
VEC_PATH = "/data/vecs.npy"
META_PATH = "/data/meta.json"
PROGRESS_PATH = "/data/progress.json"
os.makedirs(UPLOAD_DIR, exist_ok=True)

EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 50
RETRY_LIMIT = 5

client = OpenAI()

def embed_texts_with_retry(chunks):
    for attempt in range(RETRY_LIMIT):
        try:
            resp = client.embeddings.create(model=EMBED_MODEL, input=chunks)
            return [d.embedding for d in resp.data]
        except Exception as e:
            print(f"⚠️ Embedding error ({type(e).__name__}): {e}")
            wait = 2 ** attempt
            print(f"Retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError("Embedding failed after retries")

def save_progress(state, processed, total, message=""):
    with open(PROGRESS_PATH, "w") as f:
        json.dump(
            {"task": "reindex", "state": state, "processed": processed, "total": total, "message": message, "ts": int(time.time())},
            f,
        )

@app.route("/")
def home():
    return render_template("widget.html")

@app.route("/admin/uploader")
def admin():
    return render_template("uploader.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    fp = os.path.join(UPLOAD_DIR, file.filename)
    file.save(fp)
    return jsonify({"message": f"✅ Uploaded {file.filename}"}), 200

@app.route("/progress", methods=["GET"])
def get_progress():
    if not os.path.exists(PROGRESS_PATH):
        return jsonify({"state": "idle"})
    with open(PROGRESS_PATH) as f:
        return jsonify(json.load(f))

@app.route("/reindex", methods=["POST"])
def reindex():
    try:
        save_progress("starting", 0, 0, "Starting reindex...")
        texts, metas = [], []

        for filename in os.listdir(UPLOAD_DIR):
            fp = os.path.join(UPLOAD_DIR, filename)
            if not os.path.isfile(fp):
                continue
            try:
                with open(fp, "rb") as f:
                    data = f.read()
                try:
                    txt = data.decode("utf-8")
                except:
                    txt = data.decode("latin-1", errors="ignore")
                texts.append(txt[:8000])
                metas.append({"filename": filename})
            except Exception as e:
                print(f"⚠️ Skipping {filename}: {e}")

        total = len(texts)
        if total == 0:
            save_progress("error", 0, 0, "No files to index.")
            return jsonify({"error": "No files to index"}), 400

        all_vecs = []
        save_progress("running", 0, total, "Embedding started...")

        for i in tqdm(range(0, total, BATCH_SIZE)):
            batch = texts[i:i+BATCH_SIZE]
            vecs = embed_texts_with_retry(batch)
            all_vecs.extend(vecs)

            np.save(VEC_PATH, np.array(all_vecs))
            with open(META_PATH, "w") as mf:
                json.dump(metas[:len(all_vecs)], mf)
            save_progress("running", len(all_vecs), total, f"Embedded {len(all_vecs)}/{total}")

        np.save(VEC_PATH, np.array(all_vecs))
        with open(META_PATH, "w") as mf:
            json.dump(metas, mf)
        save_progress("done", total, total, "✅ Reindex complete.")
        return jsonify({"message": "Reindex complete.", "total": total})
    except Exception as e:
        save_progress("error", 0, 0, f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/reset_progress", methods=["POST"])
def reset_progress():
    try:
        if os.path.exists(PROGRESS_PATH):
            os.remove(PROGRESS_PATH)
        return jsonify({"message": "Progress reset successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def stats():
    stats = {"uploads": 0, "vectors": 0, "vec_size": 0}
    try:
        stats["uploads"] = len([f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))])
        if os.path.exists(VEC_PATH):
            stats["vec_size"] = os.path.getsize(VEC_PATH)
            try:
                arr = np.load(VEC_PATH)
                stats["vectors"] = len(arr)
            except Exception:
                stats["vectors"] = 0
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
