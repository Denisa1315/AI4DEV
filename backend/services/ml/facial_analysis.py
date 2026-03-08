import os
import time
import threading
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from hsemotion_onnx.facial_emotions import HSEmotionRecognizer


# ──────────────────────────────────────────────────────────
# DNN model URLs (OpenCV ResNet-SSD face detector)
# ──────────────────────────────────────────────────────────
DNN_PROTOTXT_URL = (
    "https://raw.githubusercontent.com/opencv/opencv/master"
    "/samples/dnn/face_detector/deploy.prototxt"
)
DNN_MODEL_URL = (
    "https://github.com/opencv/opencv_3rdparty/raw/"
    "dnn_samples_face_detector_20170830/"
    "res10_300x300_ssd_iter_140000.caffemodel"
)
DNN_PROTOTXT_PATH = "deploy.prototxt"
DNN_MODEL_PATH    = "res10_300x300_ssd_iter_140000.caffemodel"


# ──────────────────────────────────────────────────────────
# hsemotion label → lowercase system label
# ──────────────────────────────────────────────────────────
EMOTION_MAP = {
    "Anger":     "angry",
    "Disgust":   "disgust",
    "Fear":      "fear",
    "Happiness": "happy",
    "Neutral":   "neutral",
    "Sadness":   "sad",
    "Surprise":  "surprise",
    "Contempt":  "contempt",
}


# ──────────────────────────────────────────────────────────
# Result dataclass
# ──────────────────────────────────────────────────────────
@dataclass
class FacialResult:
    distress_score:    float          # 0-100
    dominant_emotion:  str            # lowercase system label
    emotions:          dict           # all emotion probabilities
    face_detected:     bool
    confidence:        float          # 0-100  (face size proxy)
    lighting:          str            # good | too_dark | too_bright
    timestamp:         float = field(default_factory=time.time)


# ──────────────────────────────────────────────────────────
# Main class
# ──────────────────────────────────────────────────────────
class FacialAnalyzer:
    """
    Thread-safe facial emotion analyzer.

    Pipeline per frame:
      detect face (DNN) -> preprocess -> ensemble inference
      -> normalise -> smooth -> disambiguate -> gate -> distress score

    Usage:
        facial_analyzer.warmup()           # call once at startup
        result = facial_analyzer.analyze_frame(frame)
        data   = facial_analyzer.to_dict() # for WebSocket
    """

    def __init__(self):
        self._lock            = threading.Lock()
        self._emotion_history = []
        self._history_size    = 2          # smooth over 4 frames
        self._lighting_status = "good"

        # Default result before first real analysis
        self._last_result = FacialResult(
            distress_score=50.0,
            dominant_emotion="neutral",
            emotions={v: 0.0 for v in EMOTION_MAP.values()},
            face_detected=False,
            confidence=0.0,
            lighting="good",
        )

        # 1. DNN face detector
        self._dnn_detector = self._load_dnn_detector()

        # 2. Haar cascade fallback
        self._haar = cv2.CascadeClassifier(
            cv2.data.haarcascades +
            "haarcascade_frontalface_default.xml"
        )

        # 3. Two emotion models (ensemble)
        print("[FacialAnalyzer] Loading emotion models ...")
        self._fer1 = HSEmotionRecognizer(
            model_name="enet_b0_8_best_afew"
        )
        self._fer2 = HSEmotionRecognizer(
            model_name="enet_b2_8"
        )
        print("[FacialAnalyzer] Models ready ✓")

    # ──────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────
    def analyze_frame(self, frame: np.ndarray) -> FacialResult:
        """
        Analyse a single BGR OpenCV frame.
        Falls back to last known result on any failure.
        """
        try:
            # Lighting check first
            self._lighting_status = self._check_lighting(frame)

            # Detect face
            face_roi, confidence = self._detect_best_face(frame)

            if face_roi is None:
                with self._lock:
                    self._last_result.face_detected = False
                    self._last_result.lighting      = self._lighting_status
                    self._last_result.timestamp     = time.time()
                return self._last_result

            # Preprocess face crop
            face_roi = self._preprocess_face(face_roi)

            # Ensemble inference
            emotion_label, scores = self._ensemble_predict(face_roi)

            # Build score dict
            raw_dict = {
                self._fer1.idx_to_class[i]: float(scores[i])
                for i in range(len(scores))
            }

            # Full processing pipeline
            norm_dict = self._normalise_emotions(raw_dict)
            norm_dict = self._smooth_emotions(norm_dict)
            dominant  = max(norm_dict, key=norm_dict.get)
            dominant  = self._disambiguate_sad_angry(norm_dict, dominant)
            dominant  = self._gate_low_intensity(norm_dict, dominant)
            distress  = self._calculate_distress(norm_dict)

            result = FacialResult(
                distress_score=round(distress, 2),
                dominant_emotion=dominant,
                emotions=norm_dict,
                face_detected=True,
                confidence=round(confidence, 1),
                lighting=self._lighting_status,
            )

            with self._lock:
                self._last_result = result

            return result

        except Exception as e:
            print(f"[FacialAnalyzer] Frame error: {e}")
            return self._last_result

    def analyze_from_bytes(self, image_bytes: bytes) -> FacialResult:
        """Analyse JPEG/PNG bytes sent from React frontend."""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError("Could not decode image bytes")
            return self.analyze_frame(frame)
        except Exception as e:
            print(f"[FacialAnalyzer] Bytes error: {e}")
            return self._last_result

    def to_dict(self) -> dict:
        """
        Thread-safe snapshot for Dev 2's WebSocket loop.
        Includes confidence for fusion engine weighting.
        """
        with self._lock:
            r = self._last_result
            return {
                "distress_score":   r.distress_score,
                "dominant_emotion": r.dominant_emotion,
                "emotions":         dict(r.emotions),
                "face_detected":    r.face_detected,
                "confidence":       r.confidence,
                "lighting":         r.lighting,
                "timestamp":        r.timestamp,
            }

    def warmup(self):
        """
        Pre-load both models into memory on startup.
        Prevents slow first response during demo.
        """
        print("[FacialAnalyzer] Warming up ...")
        dummy = np.zeros((112, 112, 3), dtype=np.uint8)
        self._fer1.predict_emotions(dummy, logits=False)
        self._fer2.predict_emotions(dummy, logits=False)
        print("[FacialAnalyzer] Warmup done ✓")

    def get_stats(self) -> dict:
        """Debug helper."""
        with self._lock:
            r = self._last_result
            return {
                "face_detected":    r.face_detected,
                "dominant_emotion": r.dominant_emotion,
                "distress_score":   r.distress_score,
                "lighting":         r.lighting,
                "history_length":   len(self._emotion_history),
            }

    # ──────────────────────────────────────────────────────
    # Improvement 1 — DNN face detector
    # ──────────────────────────────────────────────────────
    def _load_dnn_detector(self):
        """
        Download OpenCV ResNet-SSD face detector if not cached.
        Much more accurate than Haar cascade — handles angles,
        glasses, and low light significantly better.
        """
        if not os.path.exists(DNN_PROTOTXT_PATH):
            print("[FacialAnalyzer] Downloading DNN prototxt ...")
            try:
                urllib.request.urlretrieve(
                    DNN_PROTOTXT_URL, DNN_PROTOTXT_PATH
                )
            except Exception as e:
                print(f"[FacialAnalyzer] Prototxt download failed: {e}")
                return None

        if not os.path.exists(DNN_MODEL_PATH):
            print("[FacialAnalyzer] Downloading DNN weights (~2MB) ...")
            try:
                urllib.request.urlretrieve(DNN_MODEL_URL, DNN_MODEL_PATH)
                print("[FacialAnalyzer] DNN weights downloaded ✓")
            except Exception as e:
                print(f"[FacialAnalyzer] Weights download failed: {e}")
                return None

        try:
            net = cv2.dnn.readNetFromCaffe(
                DNN_PROTOTXT_PATH, DNN_MODEL_PATH
            )
            print("[FacialAnalyzer] DNN face detector loaded ✓")
            return net
        except Exception as e:
            print(f"[FacialAnalyzer] DNN load failed: {e}")
            return None

    def _detect_best_face(
        self, frame: np.ndarray
    ) -> tuple[Optional[np.ndarray], float]:
        """
        Detect the largest face using DNN detector.
        Falls back to Haar cascade if DNN unavailable.
        Returns (face_roi_bgr, confidence_0_to_100).
        """
        # DNN detection
        if self._dnn_detector is not None:
            h, w = frame.shape[:2]
            blob = cv2.dnn.blobFromImage(
                cv2.resize(frame, (300, 300)),
                1.0,
                (300, 300),
                (104.0, 177.0, 123.0),
            )
            self._dnn_detector.setInput(blob)
            detections = self._dnn_detector.forward()

            best_roi  = None
            best_area = 0

            for i in range(detections.shape[2]):
                det_conf = float(detections[0, 0, i, 2])
                if det_conf < 0.5:
                    continue

                box = (
                    detections[0, 0, i, 3:7]
                    * np.array([w, h, w, h])
                )
                x1, y1, x2, y2 = box.astype(int)
                area = (x2 - x1) * (y2 - y1)

                if area > best_area:
                    best_area = area
                    pad = int(min(x2-x1, y2-y1) * 0.1)
                    x1p = max(0, x1 - pad)
                    y1p = max(0, y1 - pad)
                    x2p = min(w,  x2 + pad)
                    y2p = min(h,  y2 + pad)
                    best_roi = frame[y1p:y2p, x1p:x2p]

            if best_roi is not None:
                conf = min(100.0, best_area / (h * w) * 1000)
                return best_roi, conf

        # Haar fallback
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)

        faces = self._haar.detectMultiScale(
            gray, scaleFactor=1.1,
            minNeighbors=5, minSize=(48, 48)
        )
        if len(faces) == 0:
            faces = self._haar.detectMultiScale(
                gray, scaleFactor=1.05,
                minNeighbors=3, minSize=(32, 32)
            )
        if len(faces) == 0:
            return None, 0.0

        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        pad = int(min(w, h) * 0.1)
        x1  = max(0, x - pad)
        y1  = max(0, y - pad)
        x2  = min(frame.shape[1], x + w + pad)
        y2  = min(frame.shape[0], y + h + pad)

        conf = min(
            100.0,
            (w * h) / (frame.shape[0] * frame.shape[1]) * 1000
        )
        return frame[y1:y2, x1:x2], conf

    # ──────────────────────────────────────────────────────
    # Improvement 2 — Face preprocessing
    # ──────────────────────────────────────────────────────
    def _preprocess_face(self, face_roi: np.ndarray) -> np.ndarray:
        """
        Clean face crop before emotion inference.
          1. Resize to 224x224
          2. Denoise — removes webcam grain
          3. CLAHE  — improves contrast in dim lighting
          4. Sharpen — enhances brow and mouth features
        """
        face = cv2.resize(face_roi, (224, 224))

        face = cv2.fastNlMeansDenoisingColored(
            face, None, 5, 5, 7, 21
        )

        lab     = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        l       = clahe.apply(l)
        lab     = cv2.merge((l, a, b))
        face    = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        kernel = np.array([
            [ 0,   -0.5,  0  ],
            [-0.5,  3.0, -0.5],
            [ 0,   -0.5,  0  ],
        ])
        face = cv2.filter2D(face, -1, kernel)

        return face

    # ──────────────────────────────────────────────────────
    # Improvement 3 — Two-model ensemble
    # ──────────────────────────────────────────────────────
    def _ensemble_predict(
        self, face_roi: np.ndarray
    ) -> tuple[str, list]:
        """
        Average softmax scores from both models.
        Reduces individual model bias — especially for sad/angry.
        """
        _, scores1 = self._fer1.predict_emotions(
            face_roi, logits=False
        )
        _, scores2 = self._fer2.predict_emotions(
            face_roi, logits=False
        )

        avg = [
            (float(scores1[i]) + float(scores2[i])) / 2.0
            for i in range(len(scores1))
        ]

        dominant_idx   = avg.index(max(avg))
        dominant_label = self._fer1.idx_to_class[dominant_idx]

        return dominant_label, avg

    # ──────────────────────────────────────────────────────
    # Improvement 4 — Lighting quality check
    # ──────────────────────────────────────────────────────
    def _check_lighting(self, frame: np.ndarray) -> str:
        """
        Returns 'good', 'too_dark', or 'too_bright'.
        Shown in React explainability panel.
        Bad lighting reduces confidence and down-weights
        facial score in the fusion engine.
        """
        gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))

        if brightness < 50:
            return "too_dark"
        elif brightness > 210:
            return "too_bright"
        return "good"

    # ──────────────────────────────────────────────────────
    # Processing pipeline helpers
    # ──────────────────────────────────────────────────────
    def _normalise_emotions(self, raw: dict) -> dict:
        """Map hsemotion labels to lowercase. Normalise to sum = 1."""
        norm = {}
        for label, score in raw.items():
            key       = EMOTION_MAP.get(label, label.lower())
            norm[key] = round(float(score), 4)

        total = sum(norm.values())
        if total > 0:
            norm = {k: round(v / total, 4) for k, v in norm.items()}

        return norm

    def _smooth_emotions(self, emotions: dict) -> dict:
        """
        Weighted temporal smoothing over last 4 frames.
        Most recent frame weighted highest.
        Eliminates single-frame noise without losing responsiveness.
        """
        self._emotion_history.append(emotions)
        if len(self._emotion_history) > self._history_size:
            self._emotion_history.pop(0)

        n            = len(self._emotion_history)
        weights      = [i + 1 for i in range(n)]
        total_weight = sum(weights)

        smoothed = {}
        for emotion in emotions:
            weighted_sum = sum(
                self._emotion_history[i].get(emotion, 0) * weights[i]
                for i in range(n)
            )
            smoothed[emotion] = round(
                weighted_sum / total_weight, 4
            )

        return smoothed

    def _disambiguate_sad_angry(
        self,
        emotions: dict,
        dominant: str,
    ) -> str:
        """
        Sad and angry share brow-furrow geometry.
        Use score ratios and co-occurring fear to choose.
        """
        sad   = emotions.get("sad",   0)
        angry = emotions.get("angry", 0)
        fear  = emotions.get("fear",  0)

        if dominant in ("sad", "angry"):
            diff = abs(sad - angry)

            if diff < 0.15:
                if fear > 0.15:
                    return "fear"
                if angry > sad and angry > 0.35:
                    return "angry"
                if sad > angry and sad > 0.35:
                    return "sad"
                return "neutral"

        return dominant

    def _gate_low_intensity(
        self,
        emotions: dict,
        dominant: str,
    ) -> str:
        """
        If dominant score is below threshold the expression
        is too subtle to classify confidently — return neutral.
        """
        thresholds = {
            "angry":    0.25,
            "sad":      0.20,
            "fear":     0.20,
            "happy":    0.25,
            "surprise": 0.28,
            "disgust":  0.18,
            "contempt": 0.15,
            "neutral":  0.10,
        }
        score     = emotions.get(dominant, 0)
        threshold = thresholds.get(dominant, 0.20)

        return "neutral" if score < threshold else dominant

    def _calculate_distress(self, emotions: dict) -> float:
        """
        Weighted distress score for mental health context.

        Primary:   sad x 0.35 + fear x 0.35
        Secondary: angry x 0.20
        Minor:     disgust x 0.10 + contempt x 0.05
        Reducer:   happy x 0.15

        Output: 0-100
        """
        raw = (
            emotions.get("sad",      0) * 0.35 +
            emotions.get("fear",     0) * 0.35 +
            emotions.get("angry",    0) * 0.20 +
            emotions.get("disgust",  0) * 0.10 +
            emotions.get("contempt", 0) * 0.05
        )
        reduction = emotions.get("happy", 0) * 0.15
        return min(100.0, max(0.0, raw - reduction) * 100)


# ──────────────────────────────────────────────────────────
# Singleton — import everywhere
# ──────────────────────────────────────────────────────────
facial_analyzer = FacialAnalyzer()