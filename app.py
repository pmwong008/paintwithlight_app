from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
from picamera2 import Picamera2
import cv2, numpy as np, time, os
import threading, requests, cv2, mediapipe as mp, time
import os
from dotenv import load_dotenv
from email.message import EmailMessage
import smtplib

load_dotenv()

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

os.makedirs("static/gallery", exist_ok=True)
TEMP_FILE = "static/temp.jpg"
capture_done = False

# MediaPipe setup 
mp_hands = mp.solutions.hands 
hands = mp_hands.Hands()

app = Flask(__name__)
picam2 = Picamera2()

config = picam2.create_video_configuration()
picam2.configure(config)
picam2.start()

def gesture_loop():
    frame_count = 0
    cooldown_until = 0

    while True:
        frame = picam2.capture_array()
        if frame is None:
            continue

        # Downscale for faster processing
        small = cv2.resize(frame, (320, 240))
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        frame_count += 1

        # Only run detection every 5th frame
        if frame_count % 5 != 0:
            continue

        # Skip detection if still in cooldown
        if time.time() < cooldown_until:
            continue

        results = hands.process(rgb)

        if results.multi_hand_landmarks:
            print("✋ Hand detected! Triggering capture...")
            try:
                requests.post("http://127.0.0.1:5000/capture", data={"exposure":6})
            except Exception as e:
                print("Error triggering capture:", e)

            # Set cooldown (e.g. 6 seconds)
            cooldown_until = time.time() + 6

# Start gesture detection in background
gesture_thread = threading.Thread(target=gesture_loop, daemon=True)
gesture_thread.start()


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
    global capture_done
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
            time.sleep(0.05)  # ~5 fps

        if not frames:
            raise RuntimeError("No frames captured during exposure")

        # Stack frames into one image
        stacked = stack_frames(frames)
        print(f"Stacked image shape: {stacked.shape}")

        # Ensure static folder exists
        os.makedirs("static", exist_ok=True)
        cv2.imwrite(TEMP_FILE, stacked)
        print(f"Saved stacked image to {TEMP_FILE}")
        capture_done = True
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


@app.route("/status") 
def status(): 
    global capture_done 
    return jsonify({"captured": capture_done})

@app.route("/review")
def review():
    # Make sure temp.jpg exists before rendering
    if os.path.exists("static/temp.jpg"):
        return render_template("review.html", file="temp.jpg")
    else:
        # If no temp image, go back to index
        return redirect(url_for("index"))



@app.route("/keep", methods=["POST"])
def keep():
    global capture_done
    timestamp = int(time.time())
    saved_file = f"static/gallery/photo_{timestamp}.jpg"
    
    os.rename(TEMP_FILE, saved_file)
    enforce_gallery_limit()
    capture_done = False  # Reset capture_done flag
    return redirect(url_for("index"))

@app.route("/discard", methods=["POST"])
def discard():
    global capture_done
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
    capture_done = False  # Reset capture_done flag
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

@app.route("/share/<filename>", methods=["POST"])
def share(filename):
    data = request.get_json()
    recipient = data.get("recipient")
    filepath = os.path.join("static/gallery", filename)

    if not recipient:
        return jsonify({"message": "No recipient provided"}), 400

    msg = EmailMessage()
    msg["Subject"] = "Photo from Pi"
    msg["From"] = os.environ.get("SMTP_USER")  # configured sender
    msg["To"] = recipient
    msg.set_content("Here is the photo you requested.")
    with open(filepath, "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="jpeg", filename=filename)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS"))
            smtp.send_message(msg)
        return jsonify({"message": f"Photo sent to {recipient}!"})
    except Exception as e:
        return jsonify({"message": f"Error sending email: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
