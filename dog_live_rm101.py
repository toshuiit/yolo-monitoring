import cv2
import os
from ultralytics import YOLO
from datetime import datetime, timedelta
import numpy as np
from email_alert import send_email_alert
import time

# === CONFIGURATION ===

model_path = "yolov8n.pt"  # switched to nano model for speed
model = YOLO(model_path)

stream_url = "rtsp://username:password@172.X.X.X:554/cam/realmonitor?channel=1&subtype=0"

conf_threshold = 0.6
frame_interval_seconds = 1.5  # increased interval slightly
trigger_threshold = 2

door_roi = (200, 580, 925, 800)  # x1, y1, x2, y2

alert_cooldown = 600  # seconds

last_alert_time = datetime.min

def is_inside_roi(box, roi):
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    rx1, ry1, rx2, ry2 = roi
    return rx1 <= cx <= rx2 and ry1 <= cy <= ry2

def can_send_alert():
    global last_alert_time
    if datetime.now() - last_alert_time > timedelta(seconds=alert_cooldown):
        last_alert_time = datetime.now()
        return True
    return False

def open_stream(url):
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print("❌ Failed to connect to the camera stream.")
        return None
    return cap

cap = open_stream(stream_url)
if cap is None:
    exit(1)

fps = cap.get(cv2.CAP_PROP_FPS)
if fps == 0 or fps != fps:
    fps = 25
frame_interval = int(fps * frame_interval_seconds)
frame_count = 0

backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=True)

dog_detected_frames = 0

print(" Live monitoring started. Press 'q' to quit.")

MAX_RETRY = 5
retry_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        retry_count += 1
        print(f"⚠️ Failed to read frame. Retry {retry_count}/{MAX_RETRY}")
        if retry_count >= MAX_RETRY:
            print(" Reconnecting to stream...")
            cap.release()
            time.sleep(2)
            cap = open_stream(stream_url)
            if cap is None:
                print("❌ Reconnect failed. Waiting 10 seconds before retrying.")
                time.sleep(10)
            retry_count = 0
        continue
    retry_count = 0

    frame_count += 1
    if frame_count % frame_interval != 0:
        continue

    height, width = frame.shape[:2]
    rx1, ry1, rx2, ry2 = door_roi

    # Clamp ROI
    rx1 = max(0, min(rx1, width - 1))
    rx2 = max(0, min(rx2, width - 1))
    ry1 = max(0, min(ry1, height - 1))
    ry2 = max(0, min(ry2, height - 1))

    roi_frame = frame[ry1:ry2, rx1:rx2]
    if roi_frame.size == 0:
        print("❌ Empty ROI. Skipping frame.")
        continue

    # Motion detection on ROI only
    fg_mask = backSub.apply(roi_frame)
    _, thresh = cv2.threshold(fg_mask, 244, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=2)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    motion_detected = any(cv2.contourArea(cnt) > 500 for cnt in contours)

    if not motion_detected:
        dog_detected_frames = 0
        continue  # skip YOLO if no motion

    # Run YOLO only on ROI to save CPU
    yolo_results = model(roi_frame)

    dog_detected = False

    for box, conf, cls_id in zip(yolo_results[0].boxes.xyxy.tolist(),
                                yolo_results[0].boxes.conf.tolist(),
                                yolo_results[0].boxes.cls.tolist()):
        if conf < conf_threshold:
            continue
        if int(cls_id) == 16:  # dog class id
            dog_detected = True
            break

    if dog_detected:
        dog_detected_frames += 1
    else:
        dog_detected_frames = 0

    if dog_detected_frames >= trigger_threshold:
        if can_send_alert():
            print(" Violation detected: Dog in ROI, sending alert...")
            send_email_alert("Live Stream", "Dog Detected at RM101 Gate")

        dog_detected_frames = 0

cap.release()
cv2.destroyAllWindows()
print(" Monitoring stopped.")
