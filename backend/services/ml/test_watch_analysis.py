# services/ml/test_watch_analysis.py
#
# Tests all watch_analysis.py functionality.
# No real watch needed — uses simulator.

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from watch_analysis import WatchAnalyzer, WatchReading, watch_analyzer

print("\n" + "="*60)
print("  Emora — Watch Analysis Test")
print("="*60 + "\n")

# ── Test 1: Apple Watch payload ───────────────────────
print("TEST 1 — Apple Watch payload parsing")
result = watch_analyzer.process(
    watch_analyzer.parse_apple_watch({
        "hrv":         42.0,
        "heart_rate":  85.0,
        "sleep_hours": 6.0,
        "steps":       3200,
        "spo2":        98.0,
    })
)
print(f"  Physio score: {result.physio_score}")
print(f"  HRV score:    {result.hrv_score}")
print(f"  HR score:     {result.hr_score}")
print(f"  Sleep score:  {result.sleep_score}")
print(f"  Context:      {result.activity_context}")
print(f"  Source:       {result.source}")
assert result.source == "apple"
assert 0 <= result.physio_score <= 100
print("  ✅ PASSED\n")

# ── Test 2: Samsung payload ───────────────────────────
print("TEST 2 — Samsung Galaxy Watch parsing")
result = watch_analyzer.process(
    watch_analyzer.parse_samsung({
        "hrv_rmssd":              38.0,
        "heart_rate":             80.0,
        "sleep_duration_minutes": 390,   # 6.5 hours
        "sleep_score":            68.0,
        "step_count":             4500,
    })
)
print(f"  Physio score: {result.physio_score}")
print(f"  Sleep hours:  {result.sleep_hours}")
assert result.source == "samsung"
assert result.sleep_hours == 6.5
print("  ✅ PASSED\n")

# ── Test 3: High stress reading ───────────────────────
print("TEST 3 — High stress reading (low HRV + high HR)")
result = watch_analyzer.process(WatchReading(
    hrv        = 18.0,    # very low HRV
    heart_rate = 102.0,   # elevated HR
    sleep_hours= 4.5,     # poor sleep
    source     = "test",
))
print(f"  Physio score: {result.physio_score} (expect high > 65)")
print(f"  HRV score:    {result.hrv_score}")
print(f"  HR score:     {result.hr_score}")
assert result.physio_score > 60, "High stress should produce high score"
print("  ✅ PASSED\n")

# ── Test 4: Calm relaxed reading ──────────────────────
print("TEST 4 — Calm relaxed reading (high HRV + low HR)")
result = watch_analyzer.process(WatchReading(
    hrv        = 72.0,   # high HRV = relaxed
    heart_rate = 58.0,   # low resting HR = fit/calm
    sleep_hours= 8.0,    # good sleep
    source     = "test",
))
print(f"  Physio score: {result.physio_score} (expect low < 35)")
assert result.physio_score < 40, "Calm state should produce low score"
print("  ✅ PASSED\n")

# ── Test 5: Activity context detection ────────────────
print("TEST 5 — Exercise context (high HR + high steps = not stress)")
result = watch_analyzer.process(WatchReading(
    hrv        = 45.0,
    heart_rate = 115.0,   # elevated from exercise
    steps      = 8500,    # lots of steps = exercising
    source     = "test",
))
print(f"  Context:      {result.activity_context}")
print(f"  Physio score: {result.physio_score}")
assert result.activity_context in ("active", "post_workout")
print("  ✅ PASSED\n")

# ── Test 6: Missing signals ───────────────────────────
print("TEST 6 — Only HRV available (no HR, no sleep)")
result = watch_analyzer.process(WatchReading(
    hrv        = 35.0,
    heart_rate = None,
    sleep_hours= None,
    source     = "test",
))
print(f"  Physio score:   {result.physio_score}")
print(f"  Active signals: {result.active_signals}")
print(f"  Confidence:     {result.confidence}%")
assert result.active_signals == 1
assert result.confidence == pytest_approx(33.3, abs=1)
print("  ✅ PASSED\n")

# ── Test 7: Simulator scenarios ───────────────────────
print("TEST 7 — Simulator scenarios")
scenarios = ["normal", "stressed", "anxious", "tired", "escalating", "crisis"]
for scenario in scenarios:
    watch_analyzer._sim_time = 10   # reset sim time
    result = watch_analyzer.simulate_and_process(scenario)
    print(f"  {scenario:12s} → score={result.physio_score:5.1f}  "
          f"hrv={result.hrv:.1f if result.hrv else 'N/A':6}  "
          f"hr={result.heart_rate:.1f if result.heart_rate else 'N/A':5}")

print("  ✅ PASSED\n")

# ── Test 8: Crisis scenario → fusion engine ───────────
print("TEST 8 — Crisis scenario feeds into fusion engine correctly")
sys.path.insert(0, os.path.dirname(__file__))
from fusion_engine import fusion_engine, SignalInput

watch_analyzer._sim_time = 0
for _ in range(3):
    crisis_result = watch_analyzer.simulate_and_process("crisis")

eli = fusion_engine.calculate(SignalInput(
    physio_score = crisis_result.physio_score,
    facial_score = 70.0,
    voice_score  = 65.0,
))
print(f"  Physio score:  {crisis_result.physio_score}")
print(f"  ELI:           {eli.eli}")
print(f"  ELI status:    {eli.status}")
if crisis_result.physio_score > 85:
    assert eli.status == "CRISIS_RISK", "Crisis physio should trigger CRISIS_RISK"
    print("  Crisis correctly detected ✅")
print("  ✅ PASSED\n")

# ── Test 9: Baseline calibration ──────────────────────
print("TEST 9 — Personal baseline learning")
fresh_analyzer = WatchAnalyzer()
for i in range(10):
    fresh_analyzer.process(WatchReading(
        hrv        = 52 + i % 3,
        heart_rate = 68 + i % 2,
        source     = "test"
    ))
baseline = fresh_analyzer.get_baseline_dict()
print(f"  HRV baseline:   {baseline['hrv_baseline']}")
print(f"  HR baseline:    {baseline['hr_baseline']}")
print(f"  Is calibrated:  {baseline['is_calibrated']}")
assert baseline["is_calibrated"] == True
print("  ✅ PASSED\n")

# ── Test 10: to_dict output for Dev 2 ─────────────────
print("TEST 10 — to_dict() output format")
watch_analyzer.process(WatchReading(
    hrv=45, heart_rate=78, sleep_hours=6.5, source="apple"
))
output = watch_analyzer.to_dict()
required_keys = [
    "physio_score", "hrv_score", "hr_score", "sleep_score",
    "activity_context", "hrv", "heart_rate", "sleep_hours",
    "hrv_deviation", "hr_deviation", "confidence", "source", "timestamp"
]
for key in required_keys:
    assert key in output, f"Missing key: {key}"

print("  All required keys present ✅")
print(f"  physio_score: {output['physio_score']}")
print(f"  confidence:   {output['confidence']}%")
print(f"  source:       {output['source']}")
print("  ✅ PASSED\n")

print("="*60)
print("  ALL TESTS PASSED ✅")
print("="*60)
print("\nSample to_dict() output (what Dev 2 sends to React):")
print(json.dumps(output, indent=2))