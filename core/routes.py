from flask import Blueprint, render_template, Response, jsonify, request, redirect, url_for
from core.camera_frames import generate_frames, capture_frame, stack_frames
from core.state import State
# from .camera import picam, init_camera, close_camera    
import time
import os
from core.threads import gesture_loop

import cv2
from core.gallery import enforce_gallery_limit

bp = Blueprint('main', __name__)

TEMP_FILE = "static/temp.jpg"
cv2 = None
state = State()

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/status')
def status():
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
        state = State()
        state.exposure = exposure_value
        print(f"Exposure updated to {state.exposure}s")
        return jsonify({"message": f"Exposure set to {state.exposure}s"}), 200

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
    return render_template("review.html")

@bp.route("/keep", methods=["POST"])
def keep_capture():
    temp_path = os.path.join("static/gallery", "temp.jpg")
    if os.path.exists(temp_path):
        filename = f"capture_{int(time.time())}.jpg"
        new_path = os.path.join("static/gallery", filename)
        os.rename(temp_path, new_path)
        
        state.gallery.append(filename)
        if len(state.gallery) > 50:
            state.gallery.pop(0)
        return jsonify({"message": "Capture kept", "file": filename})
    return jsonify({"error": "No temp capture found"}), 404

@bp.route("/discard", methods=["POST"])
def discard_capture():
    temp_path = os.path.join("static/gallery", "temp.jpg")
    if os.path.exists(temp_path):
        os.remove(temp_path)
        return jsonify({"message": "Capture discarded"})
    return jsonify({"error": "No temp capture found"}), 404


@bp.route("/video_feed")
def video_feed():
    print("Starting video feed...")
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route("/gallery")
def gallery():
    # ensure scanner is off when viewing gallery
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

