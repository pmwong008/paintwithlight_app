from flask import Flask, render_template, request, redirect, url_for, Response
from picamera2 import Picamera2
import cv2, numpy as np, time, os

app = Flask(__name__)
picam2 = Picamera2()

config = picam2.create_video_configuration()
picam2.configure(config)
picam2.start()

os.makedirs("static/gallery", exist_ok=True)
TEMP_FILE = "static/temp.jpg"

def generate_frames():
    while True:
        frame = picam2.capture_array()
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def stack_frames(frames):
    print(f"Stacking {len(frames)} frames...")
    stacked = frames[0].astype(np.float32) / 255.0
    for idx, frame in enumerate(frames[1:], start=2):
        img = frame.astype("float32") / 255.0
        stacked = np.maximum(stacked, img)
        print(f"Stacked {idx} frames so far")
    stacked = np.clip(stacked * 0.9, 0, 1)
    result = (stacked * 255).astype("uint8")
    print("Stacking complete")
    return result

def enforce_gallery_limit(limit=50):
    files = sorted(
        [f for f in os.listdir("static/gallery") if f.endswith(".jpg")],
        key=lambda f: os.path.getmtime(os.path.join("static/gallery", f))
    )
    while len(files) > limit:
        oldest = files.pop(0)
        os.remove(os.path.join("static/gallery", oldest))
        print(f"Deleted old photo: {oldest}")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/capture", methods=["POST"])
def capture():
    try:
        exposure = int(request.form.get("exposure", 3))  # seconds
        print(f"Starting capture with exposure={exposure}s")

        frames = []
        start = time.time()

        # Capture frames during exposure
        while time.time() - start < exposure:
            frame = picam2.capture_array()
            if frame is None:
                print("Warning: Frame returned None, skipping")
                # raise ValueError("Camera returned no frame")
                continue
            else:
                print(f"Captured frame with shape {frame.shape}")
            frames.append(frame)
            print(f"Captured frame {len(frames)} with shape {frame.shape}")
            time.sleep(0.1)  # ~10 fps

        if not frames:
            raise RuntimeError("No frames captured during exposure")

        # Stack frames into one image
        stacked = stack_frames(frames)
        print(f"Stacked image shape: {stacked.shape}")

        # Ensure static folder exists
        os.makedirs("static", exist_ok=True)
        cv2.imwrite(TEMP_FILE, stacked)
        print(f"Saved stacked image to {TEMP_FILE}")

        return render_template("review.html", filename=TEMP_FILE)

    except Exception as e:
        # Log error to console for debugging
        print("Error in capture():", e)

        # Return a friendly error page
        return f"""
        <h1>Capture Failed</h1>
        <p>Something went wrong: {e}</p>
        <p><a href='{url_for("index")}'>Back to preview</a></p>
        """, 500


@app.route("/keep", methods=["POST"])
def keep():
    timestamp = int(time.time())
    saved_file = f"static/gallery/photo_{timestamp}.jpg"
    
    os.rename(TEMP_FILE, saved_file)
    enforce_gallery_limit()
    return redirect(url_for("index"))

@app.route("/discard", methods=["POST"])
def discard():
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
    return redirect(url_for("index"))

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/gallery")
def gallery():
    files = [f for f in os.listdir("static/gallery") if f.endswith(".jpg")]
    # Sort by timestamp (newest first)
    files.sort(reverse=True)
    return render_template("gallery.html", files=files)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
