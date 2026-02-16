
import os

def enforce_gallery_limit(limit=50):
    files = sorted(
        [f for f in os.listdir("static/gallery") if f.endswith(".jpg")],
        key=lambda f: os.path.getmtime(os.path.join("static/gallery", f))
    )
    while len(files) > limit:
        oldest = files.pop(0)
        os.remove(os.path.join("static/gallery", oldest))
        print(f"Deleted old photo: {oldest}")
