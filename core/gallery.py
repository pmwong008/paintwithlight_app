
import os
import time

def enforce_gallery_limit(limit=50):
    files = sorted(
        [f for f in os.listdir("static/gallery") if f.endswith(".jpg")],
        key=lambda f: os.path.getmtime(os.path.join("static/gallery", f))
    )
    while len(files) > limit:
        oldest = files.pop(0)
        os.remove(os.path.join("static/gallery", oldest))
        print(f"Deleted old photo: {oldest}")


def keep_capture():
    temp_path = os.path.join("static/gallery", "temp.jpg")
    if os.path.exists(temp_path):
        filename = f"capture_{int(time.time())}.jpg"
        new_path = os.path.join("static/gallery", filename)
        os.rename(temp_path, new_path)
        print(f"Capture kept: {filename}")
        enforce_gallery_limit()
        return True
    print("No temp capture found to keep")
    return False

def discard_capture():
    temp_path = os.path.join("static/gallery", "temp.jpg")
    if os.path.exists(temp_path):
        os.remove(temp_path)
        print("Capture discarded")
        return True
    print("No temp capture found to discard")
    return False