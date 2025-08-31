import os
import cv2
import time
import threading
from datetime import datetime
from email_alert import send_email_alert

# === ENVIRONMENT CONFIGURATION FOR FFmpeg ===
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|loglevel;quiet"

# === CONFIGURATION ===
stream_url = "rtsp://username:password@172.X.X.X:554/cam/realmonitor?channel=1&subtype=0"
handle_roi_norm = {"x": 44.76, "y": 41.48, "width": 11.31, "height": 5.20}

frame_interval_seconds = 0.5
violation_duration_threshold = 120    # 2 minutes
alert_cooldown = 1200                 # 20 minutes

# Directories for logs and snapshots
log_file = "/data/door-monitoring/door_open.log"
snapshot_dir = "/data/door-monitoring/snapshots"
os.makedirs(snapshot_dir, exist_ok=True)

# === LOG HELPER ===
def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(log_file, 'a') as f:
        f.write(full_msg + "\n")

# === ROI UTILITY ===
def get_handle_roi(frame_w, frame_h):
    x = int(handle_roi_norm["x"]/100 * frame_w)
    y = int(handle_roi_norm["y"]/100 * frame_h)
    w = int(handle_roi_norm["width"]/100 * frame_w)
    h = int(handle_roi_norm["height"]/100 * frame_h)
    return (x, y, x + w, y + h)

# === PERSON DETECTION UTILITY ===
def is_person_in_front_of_handle(frame):
    # Load the pre-trained body detection classifier (Haar Cascade)
    person_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_fullbody.xml")
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    bodies = person_cascade.detectMultiScale(gray, 1.1, 1)

    for (x, y, w, h) in bodies:
        # Check if the body is in front of the door handle area
        handle_roi = get_handle_roi(frame.shape[1], frame.shape[0])
        if x < handle_roi[2] and y < handle_roi[3] and x + w > handle_roi[0] and y + h > handle_roi[1]:
            return True
    return False

# === THREADED VIDEO READER ===
class VideoStreamThread:
    def __init__(self, src_url):
        self.cap = cv2.VideoCapture(src_url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            raise IOError("Cannot open stream")
        self.ret, self.frame = self.cap.read()
        self.running = True
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            self.ret, self.frame = ret, frame
            time.sleep(0.01)

    def read(self):
        return self.ret, self.frame

    def stop(self):
        self.running = False
        self.cap.release()

# === INITIALIZATION ===
try:
    vs = VideoStreamThread(stream_url)
except Exception as e:
    log(f"❌ Failed to open stream: {e}")
    exit(1)

backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=25, detectShadows=True)

last_alert_time = datetime.min
violation_start_time = None
violation_active = False
last_time = time.time()

log(" Door handle monitoring started (headless).")

# === MAIN LOOP ===
try:
    while True:
        now_time = time.time()
        if now_time - last_time < frame_interval_seconds:
            time.sleep(0.05)
            continue
        last_time = now_time

        ret, frame = vs.read()
        if not ret or frame is None:
            log("⚠️ Failed to read frame; retrying...")
            time.sleep(1)
            continue

        h, w = frame.shape[:2]
        roi = get_handle_roi(w, h)
        roi_frame = frame[roi[1]:roi[3], roi[0]:roi[2]]

        fg = backSub.apply(roi_frame)
        _, thresh = cv2.threshold(fg, 244, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion = any(cv2.contourArea(cnt) > 100 for cnt in contours)

        current_dt = datetime.now()

        # Check for motion and make sure no person is in front of the handle
        if motion and not is_person_in_front_of_handle(frame):
            if violation_start_time is None:
                violation_start_time = current_dt
            elif (current_dt - violation_start_time).total_seconds() >= violation_duration_threshold:
                if not violation_active and (current_dt - last_alert_time).total_seconds() >= alert_cooldown:
                    log("!!! Violation: Handle missing for 2+ minutes. Sending alert.")
                    send_email_alert("Live Stream", "KD Ground Lab Door open for 2 minutes")
                    last_alert_time = current_dt
                    violation_active = True

                    # Save snapshot on violation
                    fname = current_dt.strftime("violation_%Y%m%d_%H%M%S.jpg")
                    path = os.path.join(snapshot_dir, fname)
                    cv2.imwrite(path, frame)
                    log(f" Snapshot saved: {path}")
        else:
            violation_start_time = None
            violation_active = False

except KeyboardInterrupt:
    log("Interrupt received. Shutting down...")

finally:
    vs.stop()
    log("✅ Monitoring stopped cleanly.")
