# blob_processor.py

import cv2
import mediapipe as mp
from ultralytics import YOLO
import os
import sys
import time
import argparse

# ————————————————————————— Argument Parsing —————————————————————————
parser = argparse.ArgumentParser(description="Process video with blob overlays.")
parser.add_argument("input_video",  help="Path to input video file")
parser.add_argument("output_video", help="Path to output video file")
args = parser.parse_args()

input_video  = args.input_video
output_video = args.output_video

# ————————————————————————— Configuration —————————————————————————
USE_MEDIAPIPE = True
USE_YOLO      = True
TEST_MODE     = False   # if True, process only first 200 frames

# ——————————————————————— Initialize Models ———————————————————————
pose = None
if USE_MEDIAPIPE:
    mp_pose = mp.solutions.pose
    mp_draw = mp.solutions.drawing_utils
    pose = mp_pose.Pose(static_image_mode=False,
                        model_complexity=2,
                        smooth_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5)

yolo_model = YOLO("yolov8n.pt") if USE_YOLO else None

# ————————————————————————— Load Video —————————————————————————
cap = cv2.VideoCapture(input_video)
if not cap.isOpened():
    print("❌ Error: Could not open video.")
    sys.exit(1)

frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
if TEST_MODE:
    frame_count = min(frame_count, 200)

fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# ————————————————————— Video Writer Setup —————————————————————
os.makedirs(os.path.dirname(output_video), exist_ok=True)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out    = cv2.VideoWriter(output_video, fourcc, fps, (w, h))

# ————————————————————— Startup Print —————————————————————
print(f"Processing {frame_count} frames from: {os.path.basename(input_video)}")

# ——————————————————————— Helper: ASCII Bar —————————————————————
def ascii_bar(current, total, length=30):
    pct = current / total
    filled = int(length * pct)
    bar = "#" * filled + "-" * (length - filled)
    return f"[{bar}] {int(pct*100)}%"

# ————————————————————————— Main Loop —————————————————————————
for i in range(1, frame_count + 1):
    ret, frame = cap.read()
    if not ret:
        break

    # — YOLO overlay — 
    if yolo_model:
        results = yolo_model(frame, verbose=False)
        frame   = results[0].plot()

    # — MediaPipe overlay —
    if pose:
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)
        if results.pose_landmarks:
            spec = mp_draw.DrawingSpec(color=(255,255,255), thickness=2, circle_radius=2)
            mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS, spec, spec)
            # (Extra connections omitted for brevity, re-use yours.)

    out.write(frame)

    # ——————— Terminal Progress Prints ———————
    # 1) frame counter (parsed by Flask)
    print(f"Frame {i}/{frame_count}")
    # 2) nice ASCII bar (for your terminal)
    print(ascii_bar(i, frame_count), end="\r", flush=True)

# ————————————————————————— Cleanup —————————————————————————
cap.release()
out.release()
cv2.destroyAllWindows()
print()  # newline after final carriage‐return bar
print(f"✅ Done. Saved output to: {output_video}")
