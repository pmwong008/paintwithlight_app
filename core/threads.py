import threading
import time
from core.gestures_detector  import hands, pose, HandLandmark, PoseLandmark
from core.camera_frames import close_camera, capture_frame, stack_frames
import cv2
import mediapipe as mp
from core.gallery import enforce_gallery_limit, discard_capture, keep_capture
from core.state import state

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
    print("Gesture loop started")
    last_log = 0
    last_action = 0
    while state.running:
        now = time.time()

        # Log mode every 2s
        if now - last_log > 2:
            print("Current gesture mode:", state.gesture_mode)
            last_log = now

        gesture = check_for_gesture()
        if gesture and now - last_action > 2:
            print("Gesture detected:", gesture)

            if state.gesture_mode == "capture" and gesture == "wrist_above_nose":
                state.capture_requested = True
                trigger_capture()
                print("trigger_capture called from gesture_loop")
                

            elif state.gesture_mode == "review":
                if gesture == "thumbs_up":
                    print("Gesture → keep")
                    # trigger keep logic
                elif gesture == "thumbs_down":
                    print("Gesture → discard")
                    # trigger discard logic

            elif state.gesture_mode == "gallery":
                if gesture == "scroll_up":
                    state.gallery_index = max(0, state.gallery_index - 1)
                    print("Gesture → scroll up, index:", state.gallery_index)
                elif gesture == "scroll_down":
                    state.gallery_index = min(len(state.gallery)-1, state.gallery_index + 1)
                    print("Gesture → scroll down, index:", state.gallery_index)

            last_action = now

        time.sleep(0.1)  # keep loop responsive

# threads.py
# from core.state import state

def check_for_gesture():
    if state.camera is None:
        return None

    success, frame = state.camera.read()
    print("Camera read success in check_for_gesture:", success, "Frame type:", type(frame))

    if not success:
        print("Camera read failed in check_for_gesture")
        return None

    # Convert to RGB for MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hands_results = hands.process(rgb)
    pose_results = pose.process(rgb)
    # ... landmark logic here ...


    # --- Capture mode: both wrists above nose ---
    if state.gesture_mode == "capture" and pose_results.pose_landmarks:
        nose = pose_results.pose_landmarks.landmark[PoseLandmark.NOSE]
        left_wrist = pose_results.pose_landmarks.landmark[PoseLandmark.LEFT_WRIST]
        right_wrist = pose_results.pose_landmarks.landmark[PoseLandmark.RIGHT_WRIST]
        if left_wrist.y < nose.y and right_wrist.y < nose.y:
            return "wrist_above_nose"
        

    # --- Review mode: thumbs up/down ---
    if state.gesture_mode == "review" and hands_results.multi_hand_landmarks:
        for hand_landmarks in hands_results.multi_hand_landmarks:
            thumb_tip = hand_landmarks.landmark[HandLandmark.THUMB_TIP]
            thumb_ip = hand_landmarks.landmark[HandLandmark.THUMB_IP]

            if thumb_tip.y < thumb_ip.y:  # thumb pointing up
                return "thumbs_up"
            elif thumb_tip.y > thumb_ip.y:  # thumb pointing down
                return "thumbs_down"

    # --- Gallery mode: scroll up/down ---
    if state.gesture_mode == "gallery" and hands_results.multi_hand_landmarks:
        for hand_landmarks in hands_results.multi_hand_landmarks:
            index_finger_tip = hand_landmarks.landmark[hands.HandLandmark.INDEX_FINGER_TIP]
            index_finger_pip = hand_landmarks.landmark[hands.HandLandmark.INDEX_FINGER_PIP]

            if index_finger_tip.y < index_finger_pip.y:  # finger pointing up
                return "scroll_up"
            elif index_finger_tip.y > index_finger_pip.y:  # finger pointing down
                return "scroll_down"

    return None

def trigger_capture():
    """
    Helper to request a capture from gesture or route.
    """
    with state._lock:
        if not state.capture_in_progress:
            state.capture_requested = True
            state.capture_in_progress = True
            print("Capture requested via trigger_capture()")
        else:
            print("Capture already in progress, skipping.")


'''
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
        
        if not results.pose_landmarks:
            quit_frames = 0
            capture_frames = 0
            continue
        
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
'''

# core/threads.py

def controller_loop():
    while state.is_running():
        if state.capture_requested and not state.capture_in_progress:
            # state.capture_in_progress = True
            print("Controller: capture in progress...")
            success, frame = state.camera.read()
            print("Controller: camera read success:", success, "Frame type:", type(frame))
            if success and frame is not None:
                try:
                    # Capture multiple frames for stacking
                    frames = [capture_frame() for _ in range(5)]
                    stacked = stack_frames(frames)

                    # Save to temp.jpg
                    cv2.imwrite("static/temp.jpg", cv2.cvtColor(stacked, cv2.COLOR_RGB2BGR))
                    print("Controller: stacked image saved to static/temp.jpg")
                    # state.finishing_capture()
                    state.capture_done = True
                    state.ready_for_review = True
                    state.gesture_mode = "review"
                    print("Controller: capture finished")

                except Exception as e:
                    print("Controller: error during capture", e)

        time.sleep(0.1)

