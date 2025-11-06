import os, shutil

src = "old_data"  # adjust if your backups are elsewhere
dst = "/data"

for name in ["meta.json", "vecs.npy"]:
    if os.path.exists(os.path.join(src, name)):
        shutil.copy(os.path.join(src, name), dst)
        print(f"Copied {name} → {dst}")

uploads_src = os.path.join(src, "uploads")
uploads_dst = os.path.join(dst, "uploads")
if os.path.exists(uploads_src):
    shutil.copytree(uploads_src, uploads_dst, dirs_exist_ok=True)
    print(f"Copied uploads folder → {uploads_dst}")

print("Migration complete.")
