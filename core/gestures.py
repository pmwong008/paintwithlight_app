# core/gestures.py
import time
import random

def check_for_gesture():
    """
    Stub gesture detection.
    Returns a gesture name if detected, otherwise None.
    """
    # Simulate random gesture detection
    if random.random() < 0.05:  # 5% chance each loop
        return "capture"        # gesture type
    return None
