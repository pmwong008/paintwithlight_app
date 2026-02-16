import threading
import time
from .frames import capture_frame, trigger_capture
from .state import state
from picamera2 import Picamera2
import cv2
import mediapipe as mp


picam = Picamera2()
pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)


def frame_worker(stop_event):
    while not stop_event.is_set():
        frame = capture_frame()
        # process frame here
        time.sleep(0.05)

def start_frame_thread():
    stop_event = threading.Event()
    t = threading.Thread(target=frame_worker, args=(stop_event,))
    t.start()
    return t, stop_event

def gesture_loop():
    frame_count = 0
    cooldown_until = 0
    quit_frames = 0
    capture_frames = 0
    two_hand_frames = 0

    while not state.quit_requested:
        if not state.scanner_active:
            time.sleep(0.5)
            continue

        frame = picam.capture_array()
        if frame is None:
            continue

        small = cv2.resize(frame, (320, 240))
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        frame_count += 1
        if frame_count % 5 != 0:
            continue

        if time.time() < cooldown_until:
            continue

        results = pose.process(rgb)
        '''
        if not results.pose_landmarks:
            quit_frames = 0
            capture_frames = 0
            continue
        '''
        results = pose.process(rgb)
        if results.pose_landmarks:
            print("Pose landmarks detected")
            landmarks = results.pose_landmarks.landmark
            nose = landmarks[mp.solutions.pose.PoseLandmark.NOSE]
            left_wrist = landmarks[mp.solutions.pose.PoseLandmark.LEFT_WRIST]
            right_wrist = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_WRIST]
            print(f"Nose y: {nose.y:.2f}, Left wrist y: {left_wrist.y:.2f}, Right wrist y: {right_wrist.y:.2f}")

            # Only evaluate if landmarks are visible and nose is in a reasonable range 
            if (nose.visibility > 0.5 
                and left_wrist.visibility > 0.5 
                and right_wrist.visibility > 0.5 
                and nose.y < 0.85):

                # --- Quit detection (priority) ---
                if left_wrist.y < nose.y and right_wrist.y < nose.y:
                    quit_frames += 1
                    capture_frames = 0 # prevent capture firing at same time
                    if quit_frames >= 3:   # require 3 consecutive frames
                        print("Two wrists above nose → quit")
                        quit_app()
                        # break
                else:
                    quit_frames = 0

                # --- Capture detection ---
                if (left_wrist.y < nose.y) ^ (right_wrist.y < nose.y):  # exactly one wrist above
                    capture_frames += 1
                    if capture_frames >= 3 and time.time() >= cooldown_until:  # require 3 consecutive frames
                        print("One wrist above nose → capture")
                        trigger_capture()
                        capture_frames = 0
                else:
                    capture_frames = 0
