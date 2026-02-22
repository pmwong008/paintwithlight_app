from picamera2 import Picamera2

picam = None

def init_camera():
    global picam
    if picam is None:
        try:
            picam = Picamera2()
            picam.configure(picam.create_preview_configuration())
            picam.start()
            print("Camera initialized successfully")
        except RuntimeError as e:
            print("Camera failed to initialize:", e)
            picam = None
    return picam

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

def close_camera():
    global picam
    if picam:
        try:
            picam.stop()
            print("Camera stopped")
        except Exception as e:
            print("Error stopping camera:", e)
        picam = None

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
