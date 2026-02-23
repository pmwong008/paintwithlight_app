# from picamera2 import Picamera2
import os
import cv2
import numpy as np

from core.state import state


'''
picam = None

def init_camera():
    global picam
    if picam is None:
        try:
            picam = Picamera2()
            config = picam.create_preview_configuration(main={"format": "RGB888", "size": (1280, 720)})
            picam.configure(config)
            picam.start()
            print("Camera initialized in process:", os.getpid())    
        except RuntimeError as e:
            print("Camera failed to initialize:", e)
            picam = None
    # return picam

def restart_camera():
    global picam
    if picam is not None:
        try:
            picam.stop()
            print("Camera stopped")
            picam.start()
            print("Camera restarted successfully")
        except Exception as e:
            print("Error stopping camera during restart:", e)
'''


def restart_camera():
    if state.camera is not None:
        try:
            state.camera.release()
            print("Camera released")
        except Exception as e:
            print("Error releasing camera during restart:", e)

    # Reinitialize
    state.camera = cv2.VideoCapture(0)
    if not state.camera.isOpened():
        raise RuntimeError("Failed to restart camera")
    print("Camera restarted successfully")

def close_camera():
    state.running = False
    if state.camera:
        state.camera.release()
        print("Camera released")

'''
def apply_exposure(exposure_value):
    """Map slider value (0-100) to hardware exposure time."""
    if not picam:
        print("Camera not initialized")
        return
    # Example mapping: 0–100 → 1000–101000 microseconds
    exposure_time = int(1000 + (exposure_value * 1000))
    try:
        picam.set_controls({"ExposureTime": exposure_time})
        print(f"Exposure set to {exposure_time} µs")
    except Exception as e:
        print("Error setting exposure:", e)

def capture_frame():
    
    if picam is None:
        raise RuntimeError("Camera not initialized")
    frame = picam.capture_array()
    if frame is None:
        raise RuntimeError("No frame captured")
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
'''



def apply_exposure(exposure_value: int):
    """Map slider value (0-100) to cv2 exposure setting."""
    if state.camera is None or not state.camera.isOpened():
        print("Camera not initialized")
        return

    # Example mapping: 0–100 → -7 to -1 (common v4l2 range)
    # Adjust mapping depending on your driver
    exposure_setting = int(-7 + (exposure_value / 100.0) * 6)

    try:
        state.camera.set(cv2.CAP_PROP_EXPOSURE, exposure_setting)
        print(f"Exposure set to {exposure_setting}")
    except Exception as e:
        print("Error setting exposure:", e)

def capture_frame():
    if state.camera is None or not state.camera.isOpened():
        raise RuntimeError("Camera not initialized")

    success, frame = state.camera.read()
    if not success or frame is None:
        raise RuntimeError("No frame captured")

    # Convert BGR (OpenCV default) to RGB
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def generate_frames():
    while True:
        try:
            frame = capture_frame()
            success, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            if not success:
                continue
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            print("Error in generate_frames:", e)
            break

'''
def trigger_capture(state):
    if state.cooldown_remaining() > 0:
        print("Capture on cooldown, cannot trigger capture")
        return False
    
    state.request_capture()
    print("Capture requested")
    return True
    

def generate_frames():
    while True:
        frame = picam.capture_array()
        # frame = cv2.flip(frame, 1)  # mirror preview image
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
'''
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
