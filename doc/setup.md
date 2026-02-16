# Raspberry Pi Photo App Setup

This document explains how to prepare a Raspberry Pi 5 to run the photo capture app headlessly.  
The goal: package everything into a single SD card image, so each Pi boots directly into the app via `systemd`.

---

## 1. Prepare the Raspberry Pi

- Flash Raspberry Pi OS (64‑bit recommended) onto the SD card.
- Boot the Pi and update packages:
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```


## Install dependencies

### System packages (install with apt)
These are OS‑level packages needed on Raspberry Pi / Debian systems:

```bash
sudo apt update
sudo apt install -y \
  python3 \
  python3-pip \
  python3-opencv \
  libatlas-base-dev \
  python3-picamera2 \
  libcamera-apps \
  python3-pil
```

## OR 

`sudo apt install $(cat system-requirements.txt)`


----------------- enable camera support

`sudo raspi-config`

----------------- Go to Interface Options → Camera → Enable. Reboot.

## 2. Clone the Project

- Copy repo onto the Pi:`git clone git@github.com:pmwong008/paintwithlight_app.git`

- cd paintwithlight_app

## 3. Headless Workflow

- Access the app via browser from another device on the same network:

- Find Pi's IP: `hostname -I`
- Open `http://<pi-ip>:5000` in browser
- Preview windows (cv2.imshow) should be disabled in app.py for headless mode.
- File management is done via terminal (ls, mv, rm) or SSH.

## 4. System Service

- Create a service file so the app runs on boot:

`sudo nano /etc/systemd/system/paintwithlight_app.service`

--------------------------
[Unit]
Description=Raspberry Pi Photo App
After=network.target

[Service]
ExecStart=/home/pi/REPO/venv/bin/python /home/pi/REPO/app.py
WorkingDirectory=/home/pi/REPO
Restart=always
User=pi
Environment=FLASK_ENV=production


[Install]
WantedBy=multi-user.target
-------------------------------Save and exit

## 5. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable paintwithlight_app.service
sudo systemctl start paintwithlight_app.service
```

- Check Status: `sudo systemctl status photoapp.service`
- Logs: `journalctl -u photoapp.service -f`

## 6. Workflow Summary

Boot Pi → systemd launches app.py.

App runs headlessly, serving Flask on port 5000.

Gesture detection works in background thread.

Browser auto‑redirects to review.html after capture.

User reviews, keeps/discards photo.

All photos stored in static/gallery.

## 7. Maintenance

- To stop the app: `sudo systemctl stop paintwithlight_app.service`
- To restart after code changes: `sudo systemctl restart paintwithlight_app.service`

## 9. Packaging Dependencies with Virtual Environment

To keep the app self‑contained, use a Python virtual environment (`venv`).  
This isolates dependencies from the system Python and makes the SD image reproducible.

### Create and activate venv

```bash
cd /home/pi/REPO
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies inside venv
```bash
pip install --upgrade pip
pip install flask mediapipe requests opencv-python numpy python-dotenv
```

### Freeze requirements
`pip freeze > requirements.lock`

### Reinstall On a fresh Pi
```bash
python3 -m venv venv
source venv/bin/activate
```

## run for essentials

`pip install -r requirements.txt`

## run for exact versions

`pip install -r requirements.lock`

Update the service file to run inside the virtual environment:

[Service]
ExecStart=/home/pi/REPO/venv/bin/python /home/pi/REPO/app.py
WorkingDirectory=/home/pi/REPO
Restart=always
User=pi
Environment=FLASK_ENV=production


## Project Structure

project/
│
├── app.py                  # Entry point: creates Flask app, registers blueprints
├── core/                   # Package folder for your modules
│   ├── __init__.py         # Marks this as a Python package
│   ├── routes.py           # Flask routes (Blueprint)
│   ├── frames.py           # Frame capture, generate_frames, stack_frames, trigger_capture
│   ├── threads.py          # gesture_loop, thread configs
│   ├── gallery.py          # enforce_gallery_limit, gallery utilities
│   └── state.py            # Shared state (exposure, flags, etc.)
│
├── requirements.txt
├── requirements.lock
├── system-requirements.txt
└── setup.md







