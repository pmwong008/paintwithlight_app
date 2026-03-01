# core/gestures.py
import time
import random
from core.state import state
import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose
# mp_drawing = mp.solutions.drawing_utils

# Create a global detector instance to reuse across calls
hands = mp_hands.Hands(
    # static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

pose = mp_pose.Pose(
    # static_image_mode=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

HandLandmark = mp_hands.HandLandmark
PoseLandmark = mp_pose.PoseLandmark
