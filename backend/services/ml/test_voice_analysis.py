# services/ml/test_voice_analysis.py
#
# Test voice_analysis.py — records mic continuously,
# shows live emotion scores and stress score.
# Press Ctrl+C to stop.

import sys
import os
import time
import numpy as np
import sounddevice as sd

sys.path.insert(0, os.path.dirname(__file__))
from voice_analysis import VoiceAnalyzer, SAMPLE_RATE, WINDOW_SECONDS

analyzer = VoiceAnalyzer()
analyzer.warmup()

print("\n" + "="*60)
print("  Emora — Voice Analysis Test")
print("="*60)
print("  Speak naturally into your microphone")
print("  Try different emotions:")
print("    ANGRY   → speak loudly, fast, forceful")
print("    SAD     → speak slowly, quietly, flat")
print("    FEAR    → speak with trembling, high pitch")
print("    HAPPY   → speak brightly, energetically")
print("    NEUTRAL → speak normally")
print("\n  Press Ctrl+C to stop\n")
print("="*60 + "\n")

def print_result(result):
    """Pretty print emotion results."""
    if not result.speech_detected:
        print("\r  [Listening... speak into mic]          ", end="")
        return

    # Emotion bar chart
    print("\n" + "-"*55)
    print(f"  Dominant : {result.dominant_emotion.upper():10s} | "
          f"Stress: {result.voice_stress_score:5.1f}/100 | "
          f"Conf: {result.confidence:4.1f}%")
    print("-"*55)

    for emotion, score in sorted(
        result.emotion_scores.items(),
        key=lambda x: -x[1]
    ):
        bar   = "█" * int(score * 30)
        empty = "░" * (30 - int(score * 30))
        print(f"  {emotion:8s} {score:.3f} |{bar}{empty}|")

    print("-"*55)
    f = result.features
    print(f"  Pitch: {f.get('pitch_mean',0):5.1f}Hz  "
          f"Energy: {f.get('energy_mean',0):.4f}  "
          f"Rate: {f.get('speech_rate',0):.2f}syl/s  "
          f"Pauses: {f.get('pause_density',0):.2f}")
    print()

# Main recording loop
print("Recording in 5-second windows...\n")

try:
    while True:
        print(f"\r  Recording {WINDOW_SECONDS}s window...", end="")

        # Record
        audio = sd.rec(
            int(WINDOW_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        audio = audio.flatten()

        # Analyse
        result = analyzer._process(audio)
        print_result(result)

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n\n✅ Test complete")
    print("Final state:", analyzer.to_dict())