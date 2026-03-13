# state_flags.py
import threading
from core.state import state  # import whatever you already track

# Control flags
gesture_active = True
controller_active = True

# Lock for safe access
lock = threading.Lock()

def get_state_snapshot():
    with lock:
        return {
            "exposure": state.exposure,
            "gesture_active": gesture_active,
            "controller_active": controller_active
            "gesture_mode": idle
        }
