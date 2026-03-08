# services/ml/test_fusion.py
#
# Tests fusion_engine.py and baseline_model.py together.
# Simulates a full session with different emotional states.

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fusion_engine  import fusion_engine,  SignalInput
from baseline_model import baseline_model

print("\n" + "="*60)
print("  Emora — Fusion Engine + Baseline Test")
print("="*60 + "\n")

USER = "test_user"

# ── Test 1: Normal calm state ─────────────────────────
print("TEST 1 — Calm state")
result = fusion_engine.calculate(SignalInput(
    physio_score = 30.0,
    facial_score = 20.0,
    voice_score  = 25.0,
    typing_score = 15.0,
))
print(f"  ELI:    {result.eli}  ({result.eli_label})")
print(f"  Status: {result.status}")
print(f"  Trend:  {result.eli_trend}")
assert result.eli < 35, "Calm state should be low ELI"
assert result.status == "NORMAL"
print("  ✅ PASSED\n")

# ── Test 2: High stress ───────────────────────────────
print("TEST 2 — High stress state")
result = fusion_engine.calculate(SignalInput(
    physio_score = 78.0,
    facial_score = 72.0,
    voice_score  = 80.0,
    typing_score = 65.0,
))
print(f"  ELI:    {result.eli}  ({result.eli_label})")
print(f"  Status: {result.status}")
assert result.eli > 65, "High stress should be high ELI"
print("  ✅ PASSED\n")

# ── Test 3: Crisis detection ──────────────────────────
print("TEST 3 — Crisis signal (any signal > 85)")
result = fusion_engine.calculate(SignalInput(
    physio_score = 90.0,   # above crisis threshold
    facial_score = 45.0,
    voice_score  = 50.0,
    typing_score = 40.0,
))
print(f"  ELI:    {result.eli}  ({result.eli_label})")
print(f"  Status: {result.status}")
assert result.status == "CRISIS_RISK", "Should detect crisis"
print("  ✅ PASSED\n")

# ── Test 4: Masking detection ─────────────────────────
print("TEST 4 — Masking (signals disagree by > 40 pts)")
result = fusion_engine.calculate(SignalInput(
    physio_score = 82.0,   # body very stressed
    facial_score = 75.0,   # face stressed
    voice_score  = 20.0,   # voice says fine (masking)
    typing_score = 30.0,
))
print(f"  ELI:    {result.eli}  ({result.eli_label})")
print(f"  Status: {result.status}")
assert result.status == "MASKING_DETECTED", "Should detect masking"
print("  ✅ PASSED\n")

# ── Test 5: Contradiction boost ───────────────────────
print("TEST 5 — Contradiction flag boosts ELI")
no_contra = fusion_engine.calculate(SignalInput(
    physio_score = 60.0,
    facial_score = 55.0,
    voice_score  = 58.0,
    typing_score = 50.0,
    contradiction_detected = False,
))
with_contra = fusion_engine.calculate(SignalInput(
    physio_score = 60.0,
    facial_score = 55.0,
    voice_score  = 58.0,
    typing_score = 50.0,
    contradiction_detected = True,
    contradiction_type     = "masking",
    transcript             = "I'm fine everything is okay",
))
print(f"  Without contradiction: ELI = {no_contra.eli}")
print(f"  With contradiction:    ELI = {with_contra.eli}")
assert with_contra.eli > no_contra.eli, "Contradiction should boost ELI"
print("  ✅ PASSED\n")

# ── Test 6: Missing signals ───────────────────────────
print("TEST 6 — Missing signals (no watch, no typing)")
result = fusion_engine.calculate(SignalInput(
    physio_score = None,    # no watch
    facial_score = 65.0,
    voice_score  = 70.0,
    typing_score = None,    # no typing data
))
print(f"  ELI:           {result.eli}")
print(f"  Active signals:{result.active_signals}")
print(f"  Confidence:    {result.confidence}%")
assert result.active_signals == 2
assert result.confidence == 50.0
print("  ✅ PASSED\n")

# ── Test 7: Baseline model ────────────────────────────
print("TEST 7 — Baseline model calibration")
for i in range(10):
    baseline_model.update(
        user_id      = USER,
        physio_score = 45.0 + (i % 3) * 2,
        facial_score = 30.0 + (i % 2) * 3,
        voice_score  = 40.0 + (i % 4) * 2,
        eli          = 38.0 + (i % 3) * 2,
    )

b = baseline_model.get_baseline(USER)
print(f"  Data points:     {b.data_points}")
print(f"  Is calibrated:   {b.is_calibrated}")
print(f"  ELI baseline:    {b.eli_baseline}")
print(f"  Physio baseline: {b.physio_baseline}")
assert b.is_calibrated == True
print("  ✅ PASSED\n")

# ── Test 8: Deviation detection ───────────────────────
print("TEST 8 — Deviation above personal baseline")
dev = baseline_model.get_deviation(
    user_id      = USER,
    physio_score = 85.0,   # way above their normal 47
    facial_score = 75.0,   # way above their normal 32
    voice_score  = 80.0,   # way above their normal 44
    eli          = 80.0,
)
print(f"  Physio deviation: {dev.physio_deviation:.1f}%")
print(f"  ELI deviation:    {dev.eli_deviation:.1f}%")
print(f"  Physio elevated:  {dev.physio_elevated}")
print(f"  Context: {dev.context_message}")
assert dev.physio_elevated == True
assert dev.eli_elevated    == True
print("  ✅ PASSED\n")

# ── Test 9: Full breakdown output ─────────────────────
print("TEST 9 — Full breakdown for explainability panel")
result = fusion_engine.calculate(SignalInput(
    physio_score   = 72.0,
    facial_score   = 65.0,
    voice_score    = 68.0,
    typing_score   = 45.0,
    facial_emotion = "sad",
    voice_emotion  = "fear",
    transcript     = "I'm just a bit tired",
))
output = fusion_engine.to_dict(result)
print(f"  ELI:             {output['eli']}")
print(f"  Label:           {output['eli_label']}")
print(f"  Dominant emotion:{output['dominant_emotion']}")
print(f"  Trend:           {output['eli_trend']}")
print("\n  Signal breakdown:")
for signal, data in output["breakdown"].items():
    if data["active"]:
        print(f"    {data['label']:30s} "
              f"score={data['score']:5.1f}  "
              f"weight={data['weight_pct']:4.1f}%  "
              f"contribution={data['contribution']:4.1f}")
print("  ✅ PASSED\n")

# ── Test 10: Session opening context ──────────────────
print("TEST 10 — Session opening context message")
ctx = baseline_model.get_session_opening_context(
    user_id     = USER,
    current_eli = 75.0,
    current_hrv = 35.0,    # low HRV — stressed
    sleep_hours = 5.5,     # poor sleep
    day_of_week = "Monday",
)
print(f"  Context: {ctx}")
assert len(ctx) > 10
print("  ✅ PASSED\n")

print("="*60)
print("  ALL TESTS PASSED ✅")
print("="*60)
print("\nBreakdown output (what Dev 2 sends to React):")
import json
print(json.dumps(output, indent=2))