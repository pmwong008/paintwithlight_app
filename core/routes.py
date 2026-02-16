from flask import Blueprint, bp, render_template, Response, jsonify, request, redirect, url_for
from .frames import generate_frames, capture_frame, stack_frames, trigger_capture
from .state import state
import time
import os
from .threads import start_frame_thread
from picamera2 import Picamera2
import cv2
from .gallery import enforce_gallery_limit

bp = Blueprint('main', __name__)
picam = Picamera2()
TEMP_FILE = "static/temp.jpg"
cv2 = None

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/frame')
def frame():
    frame = capture_frame()
    # convert frame to JPEG response
    return Response(frame, mimetype='image/jpeg')

@bp.route('/status')
def status():
    return jsonify({"status": "ok"})

@bp.route("/set_exposure", methods=["POST"]) 
def set_exposure(): 
    try: 
        state.exposure = int(request.form.get("exposure")) 
        print(f"Exposure updated to {state.exposure}s") 
        return jsonify({"message": f"Exposure set to {state.exposure}s"}), 200 
    except Exception as e: 
        print("Error setting exposure:", e) 
        return jsonify({"message": "Invalid exposure value"}), 400


@bp.route("/capture", methods=["POST"])
def capture():
    
    exposure = state.exposure 
    print(f"Starting capture with exposure={exposure}s")

    if state.capture_in_progress:
        return render_template("preview.html", message="Capture already in progress"), 429

    
    state.capture_in_progress = True

    try:
        # exposure = getattr(state, "exposure", 6) # fallback to 6 if not set 
        print(f"Starting capture with exposure={exposure}s")

        frames = []
        start = time.time()

        # Capture frames during exposure
        while time.time() - start < exposure:
            frame = picam.capture_array()
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

@bp.route("/review")
def review():
    state.scanner_active = False
    # Make sure temp.jpg exists before rendering
    if os.path.exists("static/temp.jpg"):
        return render_template("review.html", file="temp.jpg")
    else:
        # If no temp image, go back to index
        return redirect(url_for("index"))

@bp.route("/keep", methods=["POST"])
def keep():
    
    timestamp = int(time.time())
    saved_file = f"static/gallery/photo_{timestamp}.jpg"
    
    os.rename(TEMP_FILE, saved_file)
    enforce_gallery_limit()
    state.capture_done = False  # Reset capture_done flag
    return redirect(url_for("index"))

@bp.route("/discard", methods=["POST"])
def discard():
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
    state.capture_done = False  # Reset capture_done flag
    return redirect(url_for("index"))

@bp.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route("/gallery")
def gallery():
    state.scanner_active = False
    files = [f for f in os.listdir("static/gallery") if f.endswith(".jpg")]
    # Sort by timestamp (newest first)
    files.sort(reverse=True)
    return render_template("gallery.html", files=files)

'''
@bp.route("/share/<filename>", methods=["POST"])
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

