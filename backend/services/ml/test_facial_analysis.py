# test_facial_analysis.py

import cv2
import time
import sys
import os

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
))

from facial_analysis import facial_analyzer

facial_analyzer.warmup()

cap = cv2.VideoCapture(0)

# Camera warmup
for _ in range(30):
    cap.read()

print("Camera ready — press Q or ESC to quit\n")

last_analysis = 0

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    now = time.time()

    if now - last_analysis >= 2.0:
        result = facial_analyzer.analyze_frame(frame)
        last_analysis = now

        print(
            f"Emotion: {result.dominant_emotion:12s} | "
            f"Distress: {result.distress_score:5.1f} | "
            f"Face: {result.face_detected} | "
            f"Confidence: {result.confidence:5.1f}%"
        )

    r     = facial_analyzer.to_dict()
    color = (0, 255, 0)   if r["distress_score"] < 30 else \
            (0, 165, 255) if r["distress_score"] < 60 else \
            (0, 0, 255)

    cv2.putText(
        frame,
        f"{r['dominant_emotion']} | Distress: {r['distress_score']:.1f}",
        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2
    )

    bar = int(r["distress_score"] * 6)
    cv2.rectangle(frame, (20, 65), (20 + bar, 85), color, -1)
    cv2.rectangle(frame, (20, 65), (620, 85), (255,255,255), 1)

    y = 120
    for emotion, score in sorted(
        r["emotions"].items(), key=lambda x: -x[1]
    ):
        cv2.putText(
            frame, f"{emotion:10s} {score:.3f}",
            (20, y), cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (255,255,255), 1
        )
        bw = int(score * 200)
        cv2.rectangle(frame, (150, y-12), (150+bw, y),
                     (100,200,100), -1)
        y += 22

    cv2.imshow("Emora — Facial Analysis", frame)

    key = cv2.waitKey(100) & 0xFF
    if key == ord('q') or key == ord('Q') or key == 27:
        break

cap.release()
cv2.destroyAllWindows()
cv2.waitKey(1)
print("\nFinal state:", facial_analyzer.to_dict())
print("Done!")