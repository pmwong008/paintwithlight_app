from flask import Blueprint, render_template, Response, jsonify, request, redirect, url_for
from core.camera_frames import generate_frames, capture_frame, stack_frames
from core.state import state
 
import time
import os
from core.threads import trigger_capture, gesture_loop

import cv2
from core.gallery import enforce_gallery_limit


bp = Blueprint('main', __name__)

TEMP_FILE = "static/temp.jpg"
cv2 = None

@bp.route('/')
def index():
    state.gesture_mode = "capture"
    if state.ready_for_review:
        state.ready_for_review = False
        return redirect(url_for("main.review"))
    return render_template('index.html')

@bp.route('/status')
def status():
    # if state.ready_for_review:
        # state.ready_for_review = False  # reset flag after reporting
        # return redirect(url_for('main.review'))
    return jsonify({
        "exposure": state.exposure,
        "capture_requested": state.capture_requested,
        "capture_in_progress": state.capture_in_progress,
        "capture_done": state.capture_done,
        "cooldown_remaining": state.cooldown_remaining(),
        # "scanner_active": state.scanner_active
    })

@bp.route("/set_exposure", methods=["POST"]) 

def set_exposure(): 
    data = request.get_json()
    try:
        exposure_value = int(data.get("exposure", 6))  # default to 6 if not provided
        state.set_exposure(exposure_value)
        print(f"Exposure updated to {state.get_exposure()}s")
        return jsonify({"message": f"Exposure set to {state.get_exposure()}s"}), 200
    except Exception as e: 
        print("Error setting exposure:", e) 
        return jsonify({"message": "Invalid exposure value"}), 400

# core/routes.py
@bp.route("/shutter", methods=["POST"])
def shutter():
    if state.cooldown_remaining() > 0:
        return jsonify({
            "message": "Capture on cooldown",
            "cooldown_remaining": state.cooldown_remaining()
        }), 429

    state.request_capture()
    return jsonify({"message": "Shutter pressed, capture requested"})


# Assume `state` is imported or passed in from app.py
# If not, you can inject it via app context or a global

@bp.route("/capture", methods=["POST"])
def capture():
    if state.cooldown_remaining() > 0:
        return jsonify({
            "message": "Capture on cooldown",
            "cooldown_remaining": state.cooldown_remaining()
        }), 429  # Too Many Requests

    # Trigger capture
    state.request_capture()
    return jsonify({
        "message": "Capture requested",
        "capture_requested": state.capture_requested,
        "capture_in_progress": state.capture_in_progress
    })



@bp.route("/review")
def review():
    try:
        # Try to open or stat the file directly
        with open(TEMP_FILE, "rb") as f:
            pass  # just to trigger FileNotFoundError if missing

        # If we got here, the file exists
        state.gesture_mode = "review"
        files = ["temp.jpg"]
        return render_template("review.html", files=files)

    except FileNotFoundError:
        print("Capture failed: temp.jpg not found")
        state.gesture_mode = "capture"
        return redirect(url_for("index"))

    finally:
        print("Review route executed, gesture_mode:", state.gesture_mode)

@bp.route("/keep", methods=["POST"])
def keep():
    
    if os.path.exists(TEMP_FILE):
        filename = f"capture_{int(time.time())}.jpg"
        new_path = os.path.join("static", filename)
        os.rename(TEMP_FILE, new_path)

        state.capture_in_progress = False  # reset capture state after keeping
        state.gesture_mode = 'capture'  # reset to capture mode after keeping
        
        state.gallery.append(filename)
        enforce_gallery_limit()
        return redirect(url_for("main.index"))
    
    else:
        return jsonify({"error": "No temp capture found"}), 404

@bp.route("/discard", methods=["POST"])
def discard():
    
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
        print({"message": "Capture discarded"})
        state.capture_in_progress = False  # reset capture state after discarding
        state.gesture_mode = 'capture'  # reset to capture mode after discarding
        return redirect(url_for("main.index"))
    else:
        return jsonify({"error": "No temp capture found"}), 404


@bp.route("/video_feed")
def video_feed():
    print("Starting video feed...")
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route("/gallery")
def gallery():
    # ensure scanner is off when viewing gallery
    state.gesture_mode = "gallery"
    print("Loading gallery mode for scanning gestures...")
    files = [f for f in os.listdir("static/gallery") if f.endswith(".jpg")]
    # Sort by timestamp (newest first)
    files.sort(reverse=True)
    state.gallery_index = min(state.gallery_index, len(files)-1)  # Ensure index is in bounds
    return render_template("gallery.html", files=files, current_index=state.gallery_index)

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

# Temporary route for Chrome DevTools probing (can be removed later)
@bp.route("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_probe():
    return jsonify({})

@bp.route("/trigger_capture", methods=["POST"])
def trigger_capture_route():
    trigger_capture()
    return {"status": "capture requested"}
