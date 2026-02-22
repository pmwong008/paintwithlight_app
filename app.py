from flask import Flask, render_template, Response, jsonify, request, redirect, url_for
from core.routes import bp
from core.threads import gesture_loop

from core.frames import close_camera, trigger_capture
from core.state import State
from core.camera import init_camera
import threading
import time


app = Flask(__name__)

# init_camera()  # Initialize camera at the start of the application
# print("Camera initialized in main app")

app.register_blueprint(bp)

# Keep references to State and threads so they don't get garbage collected
state = State()

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
def controller_loop(state):
    state = State()
    while True:
        if state.quit_requested:
            quit_app()
            break
        if state.capture_requested and not state.capture_in_progress:
            if state.in_cooldown():
                print("Capture requested but in cooldown, ignoring.")
                state.capture_requested = False  # reset request to avoid repeated messages
            else:
                state.start_capture()
                trigger_capture()  # use current exposure setting
                state.finish_capture()
                state.set_cooldown(2.0)  # add cooldown after capture

        if state.capture_done:
            print("Capture done, resetting state for next capture.")
            # After capture is done, we could reset the state or perform other actions
            state.capture_done = False  # reset for next capture

        time.sleep(0.1)  # avoid busy waiting
            # state.reset_capture()


if __name__ == "__main__":
    # init_camera()  # Initialize camera at the start of the application
    # print("Camera initialized in main app")

    state = State()

    controller_thread = threading.Thread(
        target=controller_loop, 
        args=(state,), 
        daemon=True
    )
    controller_thread.start()
    print("Controller thread started.")

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

