from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
from picamera2 import Picamera2
import cv2, numpy as np, time, os
import threading, requests, cv2, mediapipe as mp, time
import os
from dotenv import load_dotenv
# from email.message import EmailMessage
import state
import sys
# import smtplib

load_dotenv()

# SMTP_USER = os.getenv("SMTP_USER")
# SMTP_PASS = os.getenv("SMTP_PASS")

os.makedirs("static/gallery", exist_ok=True)
TEMP_FILE = "static/temp.jpg"

# MediaPipe setup 
pose = mp.solutions.pose.Pose(min_detection_confidence=0.3,
                              min_tracking_confidence=0.3)

app = Flask(__name__)

picam2 = Picamera2()

config = picam2.create_video_configuration()
picam2.configure(config)
picam2.start()

# Global gesture feedback
last_gesture = None
last_gesture_time = None

def gesture_loop():
    frame_count = 0
    cooldown_until = 0
    quit_frames = 0
    capture_frames = 0
    two_hand_frames = 0

    while not state.quit_requested:
        if not state.scanner_active:
            time.sleep(0.5)
            continue

        frame = picam2.capture_array()
        if frame is None:
            continue

        small = cv2.resize(frame, (320, 240))
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        frame_count += 1
        if frame_count % 5 != 0:
            continue

        if time.time() < cooldown_until:
            continue

        results = pose.process(rgb)
        '''
        if not results.pose_landmarks:
            quit_frames = 0
            capture_frames = 0
            continue
        '''
        results = pose.process(rgb)
        if results.pose_landmarks:
            print("Pose landmarks detected")
            landmarks = results.pose_landmarks.landmark
            nose = landmarks[mp.solutions.pose.PoseLandmark.NOSE]
            left_wrist = landmarks[mp.solutions.pose.PoseLandmark.LEFT_WRIST]
            right_wrist = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_WRIST]
            print(f"Nose y: {nose.y:.2f}, Left wrist y: {left_wrist.y:.2f}, Right wrist y: {right_wrist.y:.2f}")

            # Only evaluate if landmarks are visible and nose is in a reasonable range 
            if (nose.visibility > 0.3 
                and left_wrist.visibility > 0.3 
                and right_wrist.visibility > 0.3 
                and nose.y < 0.85):

                # --- Quit detection (priority) ---
                if left_wrist.y < nose.y and right_wrist.y < nose.y:
                    quit_frames += 1
                    capture_frames = 0 # prevent capture firing at same time
                    if quit_frames >= 3:   # require 3 consecutive frames
                        print("Two wrists above nose → quit")
                        quit_app()
                        # break
                else:
                    quit_frames = 0

                # --- Capture detection ---
                if (left_wrist.y < nose.y) ^ (right_wrist.y < nose.y):  # exactly one wrist above
                    capture_frames += 1
                    if capture_frames >= 3:
                        print("One wrist above nose → capture")
                        try:
                            requests.post("http://127.0.0.1:5000/capture", data={"exposure":6})
                        except Exception as e:
                            print("Error triggering capture:", e)
                        cooldown_until = time.time() + 6
                        capture_frames = 0
                else:
                    capture_frames = 0


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

def quit_app():
    state.quit_requested = True
    # Clean up resources before quitting
    try:
        pose.close()
    except Exception:
        pass
    try:
        picam2.stop()
    except Exception:
        pass

    os._exit(0)
    # sys.exit(0) 

@app.route("/")
def index():
    state.scanner_active = True
    return render_template("index.html")

def quit_app():
    state.quit_requested = True
    # Clean up resources before quitting
    try:
        hands.close()
    except Exception:
        pass
    try:
        picam2.stop()
    except Exception:
        pass

    os._exit(0)
    # sys.exit(0) 
  


@app.route("/capture", methods=["POST"])
def capture():
    if state.capture_in_progress:
        return jsonify({"message": "Capture already in progress"}), 429
    
    state.capture_in_progress = True

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
        state.capture_done = True
        # return jsonify({"message": "Capture complete"})
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
    
    finally:
        state.capture_in_progress = False


@app.route("/status")
def status():
    return jsonify({
        "captured": state.capture_done,
        "capture_in_progress": state.capture_in_progress,
        # "last_gesture": last_gesture 
    })


@app.route("/review")
def review():
    state.scanner_active = False
    # Make sure temp.jpg exists before rendering
    if os.path.exists("static/temp.jpg"):
        return render_template("review.html", file="temp.jpg")
    else:
        # If no temp image, go back to index
        return redirect(url_for("index"))

@app.route("/keep", methods=["POST"])
def keep():
    
    timestamp = int(time.time())
    saved_file = f"static/gallery/photo_{timestamp}.jpg"
    
    os.rename(TEMP_FILE, saved_file)
    enforce_gallery_limit()
    state.capture_done = False  # Reset capture_done flag
    return redirect(url_for("index"))

@app.route("/discard", methods=["POST"])
def discard():
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
    state.capture_done = False  # Reset capture_done flag
    return redirect(url_for("index"))

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/gallery")
def gallery():
    state.scanner_active = False
    files = [f for f in os.listdir("static/gallery") if f.endswith(".jpg")]
    # Sort by timestamp (newest first)
    files.sort(reverse=True)
    return render_template("gallery.html", files=files)

'''
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
'''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
