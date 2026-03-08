# services/ml/webcam_stream.py

import cv2
import threading
import time
from services.ml.facial_analysis import facial_analyzer


class WebcamStream:
    """
    Background daemon thread.
    Continuously feeds frames to facial_analyzer.
    Dev 2 reads facial_analyzer.to_dict() in WebSocket loop.
    """

    def __init__(self, camera_index: int = 0):
        self.camera_index      = camera_index
        self.running           = False
        self.thread            = None
        self.analysis_interval = 2.0

    def start(self):
        self.running = True
        self.thread  = threading.Thread(
            target=self._run, daemon=True
        )
        self.thread.start()
        print("[WebcamStream] Started ✓")

    def stop(self):
        self.running = False
        print("[WebcamStream] Stopped")

    def _run(self):
        cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            print("[WebcamStream] ERROR: Cannot open webcam")
            return

        # Camera warmup — discard first 30 frames
        for _ in range(30):
            cap.read()

        print("[WebcamStream] Camera warmed up ✓")

        last_analysis = 0.0

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            now = time.time()
            if now - last_analysis >= self.analysis_interval:
                facial_analyzer.analyze_frame(frame)
                last_analysis = now

            time.sleep(0.033)

        cap.release()


# Singleton
webcam_stream = WebcamStream()