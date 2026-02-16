from flask import Flask
from core.routes import bp
from core.threads import start_frame_thread
from core.frames import close_camera

app = Flask(__name__)
app.register_blueprint(bp)

# Keep references to threads and stop events
threads = []
stop_events = []

def quit_app():
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

if __name__ == "__main__":
    t, stop_event = start_frame_thread()
    threads.append(t)
    stop_events.append(stop_event)

    try:
        app.run(host="0.0.0.0", port=5000, debug=True)
    except KeyboardInterrupt:
        quit_app()

