from picamera2 import Picamera2
import cv2
import numpy as np

picam = Picamera2()

def init_camera():
    picam.start()

def capture_frame():
    frame = picam.capture_array()
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
