from flask import Flask, render_template, Response, jsonify, request, redirect, url_for
from core.routes import bp
from core.threads import controller_loop, gesture_loop

# from core.frames import capture_frame, trigger_capture
from core.state import State
from core.camera_frames import init_camera, close_camera
import threading
import time

app = Flask(__name__)

# Keep references to State and threads so they don't get garbage collected
state = State()

# init_camera()  # Initialize camera at the start of the application

bp.state = state  # Inject state into routes blueprint
app.register_blueprint(bp)

def quit_app(threads, stop_events):
    """Gracefully stop threads and release resources."""
    print("Shutting down application...")

    # Signal all threads to stop
    for event in stop_events:
        event.set()

    # Wait for threads to finish
    for t in threads:
        t.join()

    # Release camera or other resources
    close_camera()

    print("Shutdown complete.")

# controller in app.py


if __name__ == "__main__":
    init_camera()  # Initialize camera at the start of the application
    print("Camera initialized in main app")

    controller_thread = threading.Thread(
        target=controller_loop, 
        args=(state,), 
        daemon=True
    )
    controller_thread.start()
    print("Controller thread started.")

    gesture_thread = threading.Thread(
        target=gesture_loop, 
        args=(state,), 
        daemon=True
    )
    gesture_thread.start()
    print("Gesture thread started.")

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

