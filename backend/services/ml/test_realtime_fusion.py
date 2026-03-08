# test_realtime_fusion.py
# Run from backend root:
#   python test_realtime_fusion.py
#
# Shows live webcam feed with ELI overlay.
# Analyses face + voice + simulated watch every 3 seconds.
# Press Q or ESC to quit.

import sys
import os

# Fix path — add backend root so 'services' package is found
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
))

import cv2
import numpy as np
import sounddevice as sd
import threading
import time

# Add backend root to path
sys.path.insert(0, os.path.dirname(__file__))

from services.ml.facial_analysis import facial_analyzer
from services.ml.voice_analysis   import voice_analyzer
from services.ml.watch_analysis   import watch_analyzer, WatchReading
from services.ml.fusion_engine    import fusion_engine, SignalInput
from services.ml.baseline_model   import baseline_model

SAMPLE_RATE    = 16000
WINDOW_SECONDS = 5

# ─────────────────────────────────────────────────────
# Shared state — updated by background threads
# ─────────────────────────────────────────────────────
state = {
    "facial":       {},
    "voice":        {},
    "watch":        {},
    "eli":          {},
    "last_voice":   0,
    "last_watch":   0,
}

# ─────────────────────────────────────────────────────
# Background voice recording thread
# ─────────────────────────────────────────────────────
def voice_thread():
    print("[Voice] Microphone thread started")
    while True:
        try:
            audio = sd.rec(
                int(WINDOW_SECONDS * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='float32'
            )
            sd.wait()
            result = voice_analyzer._process(audio.flatten())
            state["voice"]      = voice_analyzer.to_dict()
            state["last_voice"] = time.time()
        except Exception as e:
            print(f"[Voice] Error: {e}")
            time.sleep(2)

# ─────────────────────────────────────────────────────
# Simulated watch — updates every 5 seconds
# Uses "escalating" scenario so you can see ELI change
# ─────────────────────────────────────────────────────
def watch_thread():
    print("[Watch] Simulated watch thread started")
    while True:
        try:
            result = watch_analyzer.simulate_and_process("normal")
            state["watch"]      = watch_analyzer.to_dict()
            state["last_watch"] = time.time()
            time.sleep(5)
        except Exception as e:
            print(f"[Watch] Error: {e}")
            time.sleep(5)

# ─────────────────────────────────────────────────────
# Colour helpers
# ─────────────────────────────────────────────────────
def eli_color(eli: float):
    if eli < 30:   return (80,  200, 80)    # green
    if eli < 50:   return (80,  200, 200)   # cyan
    if eli < 65:   return (0,   165, 255)   # orange
    if eli < 80:   return (0,   80,  255)   # red-orange
    return                (0,   0,   220)   # red

def emotion_color(emotion: str):
    colors = {
        "happy":   (80,  220, 80),
        "neutral": (180, 180, 180),
        "sad":     (220, 130, 60),
        "angry":   (60,  60,  220),
        "fear":    (180, 60,  180),
        "surprise":(60,  220, 220),
        "disgust": (60,  180, 120),
    }
    return colors.get(emotion, (180, 180, 180))

def draw_bar(frame, x, y, w, h, value, color, bg=(50,50,50)):
    cv2.rectangle(frame, (x, y), (x+w, y+h), bg, -1)
    fill = int((value / 100) * w)
    if fill > 0:
        cv2.rectangle(frame, (x, y), (x+fill, y+h), color, -1)
    cv2.rectangle(frame, (x, y), (x+w, y+h), (100,100,100), 1)

def put_text(frame, text, x, y, color=(255,255,255), scale=0.55, thickness=1):
    cv2.putText(frame, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness,
                cv2.LINE_AA)

# ─────────────────────────────────────────────────────
# Main overlay drawing
# ─────────────────────────────────────────────────────
def draw_overlay(frame, facial, voice, watch, eli_data):
    h, w = frame.shape[:2]

    # ── Semi-transparent left panel ───────────────────
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (320, h), (20, 20, 30), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # ── Title ─────────────────────────────────────────
    put_text(frame, "Emora", 10, 28,
             color=(100, 220, 255), scale=0.8, thickness=2)
    put_text(frame, "Real-Time Fusion", 10, 50,
             color=(150, 150, 150), scale=0.45)

    # ── ELI Score (big) ───────────────────────────────
    eli   = eli_data.get("eli", 50.0)
    label = eli_data.get("eli_label", "—")
    color = eli_color(eli)

    cv2.putText(frame, f"{eli:.1f}", (10, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 2.2, color, 3, cv2.LINE_AA)
    put_text(frame, "ELI", 10, 138, color=(150,150,150), scale=0.45)
    put_text(frame, label.upper(), 80, 138, color=color, scale=0.45)

    draw_bar(frame, 10, 148, 290, 14, eli, color)

    # ── Status ────────────────────────────────────────
    status = eli_data.get("status", "—")
    status_colors = {
        "NORMAL":           (80,  200, 80),
        "MASKING_DETECTED": (0,   165, 255),
        "CRISIS_RISK":      (0,   0,   220),
        "NO_SIGNAL":        (100, 100, 100),
    }
    sc = status_colors.get(status, (180,180,180))
    put_text(frame, status, 10, 180, color=sc, scale=0.5, thickness=1)

    # Trend arrow
    trend = eli_data.get("eli_trend", "stable")
    arrow = "↑ RISING" if trend=="rising" else ("↓ FALLING" if trend=="falling" else "→ STABLE")
    trend_color = (0,80,220) if trend=="rising" else ((80,200,80) if trend=="falling" else (180,180,180))
    put_text(frame, arrow, 180, 180, color=trend_color, scale=0.45)

    # ── Dominant emotion ──────────────────────────────
    dominant = eli_data.get("dominant_emotion", "neutral")
    ec       = emotion_color(dominant)
    put_text(frame, "EMOTION", 10, 210, color=(150,150,150), scale=0.4)
    put_text(frame, dominant.upper(), 10, 232, color=ec, scale=0.65, thickness=2)

    # ── Contradiction ─────────────────────────────────
    if eli_data.get("contradiction_detected"):
        ctype = eli_data.get("contradiction_type", "").upper()
        cv2.rectangle(frame, (8, 240), (312, 260), (0, 80, 200), -1)
        put_text(frame, f"⚠ {ctype}", 12, 255,
                 color=(255, 255, 100), scale=0.5, thickness=1)
    else:
        put_text(frame, "No contradiction", 10, 255,
                 color=(80, 180, 80), scale=0.4)

    # ── Signal breakdown bars ─────────────────────────
    put_text(frame, "SIGNALS", 10, 285, color=(150,150,150), scale=0.4)

    breakdown = eli_data.get("breakdown", {})
    signals = [
        ("physio", "Watch",  watch.get("physio_score",  50)),
        ("facial", "Face",   facial.get("distress_score", 50)),
        ("voice",  "Voice",  voice.get("combined_score",  50)),
        ("typing", "Typing", 50),
    ]
    y = 300
    for key, label_s, score in signals:
        active = breakdown.get(key, {}).get("active", False)
        bc     = eli_color(score) if active else (80, 80, 80)
        put_text(frame, f"{label_s:<7}", 10, y+11, color=(180,180,180), scale=0.4)
        draw_bar(frame, 65, y, 200, 12, score if active else 0, bc)
        put_text(frame, f"{score:.0f}" if active else "N/A",
                 272, y+11, color=bc, scale=0.38)
        y += 20

    # ── Voice transcript ──────────────────────────────
    transcript = voice.get("transcript", "")
    sentiment  = voice.get("transcript_sentiment", "neutral")
    if transcript:
        # Truncate long transcripts
        display = transcript[:38] + "..." if len(transcript) > 38 else transcript
        sent_color = (80,220,80) if sentiment=="positive" else \
                     ((60,80,220) if sentiment=="negative" else (180,180,180))
        put_text(frame, "TRANSCRIPT", 10, 396, color=(150,150,150), scale=0.38)
        put_text(frame, f'"{display}"', 10, 412,
                 color=(220,220,220), scale=0.38)
        put_text(frame, sentiment.upper(), 10, 428,
                 color=sent_color, scale=0.38)
    else:
        put_text(frame, "Listening...", 10, 412,
                 color=(100,100,100), scale=0.4)

    # ── Watch data ────────────────────────────────────
    hrv = watch.get("hrv")
    hr  = watch.get("heart_rate")
    put_text(frame, "WATCH (simulated)", 10, 450,
             color=(150,150,150), scale=0.38)
    if hrv:
        put_text(frame, f"HRV: {hrv:.1f}ms  HR: {hr:.0f}bpm",
                 10, 465, color=(180,220,255), scale=0.42)

    # ── Confidence ────────────────────────────────────
    conf = eli_data.get("confidence", 0)
    put_text(frame, f"Confidence: {conf:.0f}%  Signals: {eli_data.get('active_signals',0)}/4",
             10, 490, color=(120,120,120), scale=0.38)

    # ── Bottom hint ───────────────────────────────────
    put_text(frame, "Press Q or ESC to quit",
             10, h-10, color=(80,80,80), scale=0.38)

    return frame

# ─────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────
def main():
    print("\n" + "="*55)
    print("  Emora — Real-Time Fusion Test")
    print("="*55)
    print("  Camera + Mic + Simulated Watch")
    print("  ELI updates every 3 seconds")
    print("  Press Q or ESC to quit\n")

    # Warmup
    print("Warming up models...")
    facial_analyzer.warmup()
    voice_analyzer.warmup()
    print("Models ready ✓\n")

    # Start background threads
    vt = threading.Thread(target=voice_thread, daemon=True)
    wt = threading.Thread(target=watch_thread, daemon=True)
    vt.start()
    wt.start()

    # Give watch thread a moment to get first reading
    time.sleep(1)

    # Open camera
    print("Opening camera...")
    cap = cv2.VideoCapture(0)

    # Warmup camera
    for _ in range(30):
        cap.read()
    print("Camera ready ✓\n")
    print("Running — speak into mic and look at camera\n")

    last_facial_analysis = 0
    last_fusion          = 0
    facial_interval      = 2.0   # analyse face every 2s
    fusion_interval      = 3.0   # recalculate ELI every 3s

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        now = time.time()

        # ── Facial analysis every 2 seconds ───────────
        if now - last_facial_analysis >= facial_interval:
            result = facial_analyzer.analyze_frame(frame)
            state["facial"] = facial_analyzer.to_dict()
            last_facial_analysis = now

        # ── Fusion engine every 3 seconds ─────────────
        if now - last_fusion >= fusion_interval:
            facial = state.get("facial", {})
            voice  = state.get("voice",  {})
            watch  = state.get("watch",  {})

            eli_result = fusion_engine.calculate(SignalInput(
                physio_score           = watch.get("physio_score"),
                facial_score           = facial.get("distress_score"),
                voice_score            = voice.get("combined_score"),
                typing_score           = None,
                contradiction_detected = voice.get("contradiction_detected", False),
                contradiction_type     = voice.get("contradiction_type", "none"),
                transcript             = voice.get("transcript", ""),
                facial_emotion         = facial.get("dominant_emotion", "neutral"),
                voice_emotion          = voice.get("dominant_emotion", "neutral"),
            ))

            state["eli"] = fusion_engine.to_dict(eli_result)

            # Update baseline
            baseline_model.update(
                user_id      = "demo_user",
                physio_score = watch.get("physio_score"),
                facial_score = facial.get("distress_score"),
                voice_score  = voice.get("combined_score"),
                eli          = eli_result.eli,
                hrv          = watch.get("hrv"),
                hr           = watch.get("heart_rate"),
            )

            last_fusion = now

            # Print to terminal too
            eli  = state["eli"]
            cont = " ⚠ CONTRADICTION" if eli.get("contradiction_detected") else ""
            print(f"ELI: {eli.get('eli',0):5.1f} ({eli.get('eli_label','—'):8s}) | "
                  f"Status: {eli.get('status','—'):20s} | "
                  f"Emotion: {eli.get('dominant_emotion','—'):8s} | "
                  f"Transcript: \"{state.get('voice',{}).get('transcript','...')}\""
                  f"{cont}")

        # ── Draw overlay ──────────────────────────────
        frame = draw_overlay(
            frame,
            state.get("facial", {}),
            state.get("voice",  {}),
            state.get("watch",  {}),
            state.get("eli",    {}),
        )

        cv2.imshow("Emora — Real-Time Fusion", frame)

        key = cv2.waitKey(30) & 0xFF
        if key == ord('q') or key == ord('Q') or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    cv2.waitKey(1)

    print("\n\nFinal state:")
    print(f"  ELI:     {state['eli'].get('eli', '—')}")
    print(f"  Status:  {state['eli'].get('status', '—')}")
    print(f"  Emotion: {state['eli'].get('dominant_emotion', '—')}")
    b = baseline_model.get_baseline_dict("demo_user")
    print(f"  Baseline calibrated: {b['is_calibrated']}")
    print("\nDone ✓")


if __name__ == "__main__":
    main()