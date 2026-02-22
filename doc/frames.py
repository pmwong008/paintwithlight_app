from camera_frames import picam
import cv2
import numpy as np
import os
import time
import requests
from core.state import State

def capture_frame():
    
    if picam is None:
        raise RuntimeError("Camera not initialized")
    frame = picam.capture_array()
    if frame is None:
        raise RuntimeError("No frame captured")
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


def trigger_capture(state):
    if state.cooldown_remaining() > 0:
        print("Capture on cooldown, cannot trigger capture")
        return False
    
    state.request_capture()
    print("Capture requested")
    return True
    
'''
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
