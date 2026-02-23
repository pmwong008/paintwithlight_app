# core/gestures.py
import time
import random
import mediapipe as mp
from core.state import state
import cv2

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
