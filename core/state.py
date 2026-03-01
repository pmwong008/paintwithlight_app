# core/state.py
import threading
import time
import os

class State:
    """
    Shared application state with thread-safe access.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.running = True  # Flag to control the main loop
        self.exposure = 0.5
        self.gallery = []  # List of captured images (file paths)
        self.gallery_index = 0  # Index of the current gallery image

        # Capture workflow flags
        self.capture_requested = False
        self.capture_in_progress = False
        self.capture_done = False
        self.ready_for_review = False
        self.gesture_mode = "idle"  # can be "idle", "capture_requested", "capturing", "cooldown"
        self.camera = None  # Placeholder for camera object
        # Cooldown tracking
        self._cooldown_until = 0

        # Optional scanner flag
        self.scanner_active = False

    def set_exposure(self, value: float):
        with self._lock:
            self.exposure = value

    def get_exposure(self) -> float:
        with self._lock:
            return self.exposure

    def request_capture(self):
        with self._lock:
            self.capture_requested = True
            self.capture_in_progress = True
            self.capture_done = False

    def finishing_capture(self, temp_path="static/temp.jpg"):
        with self._lock:
            try:
                # Reset capture flags
                self.capture_in_progress = True
                self.capture_requested = False
                # self.capture_done = True

                # Switch to review mode if file exists
                if os.path.exists(temp_path):
                    self.gesture_mode = "review"
                    print(f"Capture finished, file ready at {temp_path}")
                else:
                    # If no file, fall back to capture mode
                    self.gesture_mode = "capture"
                    self.capture_in_progress = False
                    print("Capture finished but no file found")

                # Start cooldown (e.g. 5 seconds)
                self._cooldown_until = time.time() + 5

            except Exception as e:
                # Always reset to safe state on error
                self.capture_in_progress = False
                self.capture_requested = False
                self.capture_done = False
                self.gesture_mode = "capture"
                print("Error finishing capture:", e)

            finally:
                print("finish_capture executed, gesture_mode:", self.gesture_mode)


    def cooldown_remaining(self) -> int:
        with self._lock:
            remaining = int(self._cooldown_until - time.time())
            return max(0, remaining)

    def set_scanner_active(self, active: bool):
        with self._lock:
            self.scanner_active = active

    def stop(self):
        with self._lock:
            self.running = False

    def is_running(self) -> bool:
        with self._lock:
            return self.running
        
state = State()  # Global state instance
    

