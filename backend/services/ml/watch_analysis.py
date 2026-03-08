# services/ml/watch_analysis.py
#
# Physiological Stress Score from Smartwatch Data
# for AffectSync.
#
# Converts raw watch readings into a single physio_score (0-100)
# which feeds directly into the fusion engine.
#
# Supported inputs:
#   - HRV (heart rate variability) — primary stress signal
#   - Heart rate (resting vs elevated)
#   - Sleep duration and quality
#   - Steps / activity (context — prevents false positives)
#   - SpO2 (blood oxygen) — optional
#
# Supported watch sources:
#   - Apple Watch (via Apple Shortcuts webhook)
#   - Samsung Galaxy Watch (via Samsung Health export)
#   - Fitbit (via Fitbit Web API)
#   - Generic / Mi Band (via webhook)
#   - Simulated (for demo when no watch connected)
#
# Personal baseline:
#   Learns user's normal HRV and HR over time.
#   Deviation from personal baseline >> raw score.

import time
import statistics
import threading
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────

@dataclass
class WatchReading:
    """
    Universal watch reading — hardware agnostic.
    All watch sources map to this structure.
    """
    # Primary signals
    hrv:          Optional[float] = None   # ms — RMSSD preferred
    heart_rate:   Optional[float] = None   # bpm
    sleep_hours:  Optional[float] = None   # hours last night
    sleep_quality:Optional[float] = None   # 0-100 if available

    # Secondary signals
    steps:        Optional[float] = None   # steps so far today
    spo2:         Optional[float] = None   # blood oxygen %
    respiratory_rate: Optional[float] = None  # breaths/min

    # Source metadata
    source:       str   = "unknown"        # apple / samsung / fitbit / generic / simulated
    timestamp:    float = field(default_factory=time.time)


@dataclass
class PhysioResult:
    """
    Processed physiological stress result.
    physio_score is what goes into the fusion engine.
    """
    physio_score:       float   # 0-100 — primary output for fusion engine

    # Sub-scores
    hrv_score:          float   # 0-100 (high HRV = low stress)
    hr_score:           float   # 0-100
    sleep_score:        float   # 0-100
    activity_context:   str     # resting / active / post_workout / sleeping

    # Raw readings (for explainability panel)
    hrv:                Optional[float]
    heart_rate:         Optional[float]
    sleep_hours:        Optional[float]

    # Deviation from personal baseline
    hrv_deviation:      float   # percentage above/below normal
    hr_deviation:       float

    # Confidence
    active_signals:     int
    confidence:         float   # 0-100

    # Source
    source:             str
    timestamp:          float = field(default_factory=time.time)


# ─────────────────────────────────────────────────────
# Population reference ranges
# Based on published research (Shaffer & Ginsberg 2017)
# ─────────────────────────────────────────────────────
HRV_REFERENCE = {
    # age_range: (low_stress_hrv, high_stress_hrv)
    # RMSSD in milliseconds
    "18-25": (60, 20),
    "26-35": (55, 18),
    "36-45": (45, 15),
    "46-55": (38, 12),
    "56+":   (30, 10),
    "default": (50, 15),
}

HR_REFERENCE = {
    "resting_normal": (60, 80),     # bpm — normal resting range
    "resting_stressed": 90,          # bpm — above this = elevated
    "active_threshold": 100,         # bpm — above this may be exercise
    "high_threshold": 110,           # bpm — definitely elevated
}

SLEEP_REFERENCE = {
    "optimal": 8.0,       # hours
    "good":    7.0,
    "fair":    6.0,
    "poor":    5.0,
    "very_poor": 4.0,
}


# ─────────────────────────────────────────────────────
# Watch Analyzer
# ─────────────────────────────────────────────────────

class WatchAnalyzer:
    """
    Converts raw smartwatch readings into a physiological
    stress score for the AffectSync fusion engine.

    Usage:
        # When Apple Watch pushes data every 30s
        reading = WatchReading(hrv=42, heart_rate=85, source="apple")
        result  = watch_analyzer.process(reading)

        # Pass to fusion engine
        fusion_engine.calculate(SignalInput(
            physio_score = result.physio_score,
            ...
        ))

        # Or read the latest cached result
        watch_analyzer.last_result.physio_score
    """

    def __init__(self):
        self._lock    = threading.Lock()
        self._history = []
        self._history_size = 20    # smooth over 20 readings

        # Personal baseline
        self._baseline = {
            "hrv":          55.0,
            "heart_rate":   70.0,
            "hrv_readings": [],
            "hr_readings":  [],
        }

        # Default result before first reading
        self._last_result = PhysioResult(
            physio_score=50.0,
            hrv_score=50.0,
            hr_score=50.0,
            sleep_score=50.0,
            activity_context="resting",
            hrv=None,
            heart_rate=None,
            sleep_hours=None,
            hrv_deviation=0.0,
            hr_deviation=0.0,
            active_signals=0,
            confidence=0.0,
            source="none",
        )

        # Simulation state
        self._sim_time      = 0
        self._sim_scenario  = "normal"

        print("[WatchAnalyzer] Ready ✓")

    # ─────────────────────────────────────────────────
    # Primary method
    # ─────────────────────────────────────────────────
    def process(self, reading: WatchReading) -> PhysioResult:
        """
        Process a single watch reading into a physio_score.
        Thread-safe — safe to call from FastAPI endpoint.
        """
        try:
            # 1. Detect activity context
            context = self._detect_activity_context(reading)

            # 2. Calculate sub-scores
            hrv_score   = self._score_hrv(reading.hrv, context)
            hr_score    = self._score_heart_rate(reading.heart_rate, context)
            sleep_score = self._score_sleep(reading.sleep_hours,
                                            reading.sleep_quality)

            # 3. Update personal baseline
            self._update_baseline(reading)

            # 4. Calculate deviations
            hrv_dev = self._deviation(
                reading.hrv, self._baseline["hrv"]
            )
            hr_dev  = self._deviation(
                reading.heart_rate, self._baseline["heart_rate"]
            )

            # 5. Count active signals and confidence
            active = sum([
                reading.hrv          is not None,
                reading.heart_rate   is not None,
                reading.sleep_hours  is not None,
            ])
            confidence = (active / 3) * 100

            # 6. Weighted fusion of sub-scores
            physio_score = self._calculate_physio_score(
                hrv_score, hr_score, sleep_score,
                active, context, hrv_dev, hr_dev
            )

            # 7. Smooth over recent history
            physio_score = self._smooth(physio_score)

            result = PhysioResult(
                physio_score=round(physio_score, 1),
                hrv_score=round(hrv_score, 1),
                hr_score=round(hr_score, 1),
                sleep_score=round(sleep_score, 1),
                activity_context=context,
                hrv=reading.hrv,
                heart_rate=reading.heart_rate,
                sleep_hours=reading.sleep_hours,
                hrv_deviation=round(hrv_dev, 1),
                hr_deviation=round(hr_dev, 1),
                active_signals=active,
                confidence=round(confidence, 1),
                source=reading.source,
            )

            with self._lock:
                self._last_result = result

            return result

        except Exception as e:
            print(f"[WatchAnalyzer] Error: {e}")
            return self._last_result

    # ─────────────────────────────────────────────────
    # HRV scoring
    # ─────────────────────────────────────────────────
    def _score_hrv(
        self,
        hrv:     Optional[float],
        context: str
    ) -> float:
        """
        Convert HRV to stress score.

        HRV is the most reliable physiological stress indicator.
        HIGH HRV = relaxed parasympathetic state = LOW stress
        LOW HRV  = stressed sympathetic state    = HIGH stress

        We use personal baseline deviation as primary signal,
        population reference as fallback.
        """
        if hrv is None:
            return 50.0

        # Skip HRV scoring during active exercise
        if context == "post_workout":
            return 50.0

        baseline_hrv = self._baseline["hrv"]

        # Personal baseline deviation (primary)
        if len(self._baseline["hrv_readings"]) >= 5:
            deviation_pct = ((baseline_hrv - hrv) / baseline_hrv) * 100
            # Positive deviation = HRV below baseline = stressed
            score = 50 + (deviation_pct * 0.8)
        else:
            # Population reference (fallback until calibrated)
            # HRV 15ms = very stressed → score 90
            # HRV 70ms = relaxed      → score 10
            if hrv <= 15:
                score = 90.0
            elif hrv >= 70:
                score = 10.0
            else:
                score = 90 - ((hrv - 15) / (70 - 15)) * 80

        return max(0.0, min(100.0, score))

    # ─────────────────────────────────────────────────
    # Heart rate scoring
    # ─────────────────────────────────────────────────
    def _score_heart_rate(
        self,
        hr:      Optional[float],
        context: str
    ) -> float:
        """
        Convert heart rate to stress score.

        Uses personal baseline + population reference.
        Accounts for activity context — elevated HR during
        exercise is not stress.
        """
        if hr is None:
            return 50.0

        # During exercise, elevated HR is expected — not stress
        if context in ("active", "post_workout") and hr < 120:
            return 30.0

        baseline_hr = self._baseline["heart_rate"]

        # Personal deviation (primary)
        if len(self._baseline["hr_readings"]) >= 5:
            deviation_pct = ((hr - baseline_hr) / baseline_hr) * 100
            score = 50 + (deviation_pct * 1.2)
        else:
            # Population reference
            low, high = HR_REFERENCE["resting_normal"]
            if hr <= high:
                score = ((hr - low) / (high - low)) * 40
            elif hr <= HR_REFERENCE["resting_stressed"]:
                score = 40 + ((hr - high) /
                              (HR_REFERENCE["resting_stressed"] - high)) * 30
            elif hr <= HR_REFERENCE["high_threshold"]:
                score = 70 + ((hr - HR_REFERENCE["resting_stressed"]) /
                              (HR_REFERENCE["high_threshold"] -
                               HR_REFERENCE["resting_stressed"])) * 20
            else:
                score = 90 + min(10, (hr - HR_REFERENCE["high_threshold"]) * 0.5)

        return max(0.0, min(100.0, score))

    # ─────────────────────────────────────────────────
    # Sleep scoring
    # ─────────────────────────────────────────────────
    def _score_sleep(
        self,
        sleep_hours:   Optional[float],
        sleep_quality: Optional[float]
    ) -> float:
        """
        Convert sleep data to stress score.

        Poor sleep elevates cortisol and impairs HRV.
        Sleep deprivation amplifies emotional reactivity.

        Score interpretation:
          8h+ good sleep → score 10-20 (low stress contribution)
          6-7h fair sleep → score 30-50
          <5h poor sleep  → score 70-90
        """
        if sleep_hours is None:
            return 40.0    # slight elevation if unknown

        # Duration score
        if sleep_hours >= SLEEP_REFERENCE["optimal"]:
            duration_score = 10.0
        elif sleep_hours >= SLEEP_REFERENCE["good"]:
            duration_score = 25.0
        elif sleep_hours >= SLEEP_REFERENCE["fair"]:
            duration_score = 45.0
        elif sleep_hours >= SLEEP_REFERENCE["poor"]:
            duration_score = 65.0
        elif sleep_hours >= SLEEP_REFERENCE["very_poor"]:
            duration_score = 80.0
        else:
            duration_score = 90.0

        # Quality modifier if available
        if sleep_quality is not None:
            quality_modifier = (100 - sleep_quality) * 0.2
            duration_score   = min(100.0, duration_score + quality_modifier)

        return duration_score

    # ─────────────────────────────────────────────────
    # Activity context detection
    # ─────────────────────────────────────────────────
    def _detect_activity_context(self, reading: WatchReading) -> str:
        """
        Detect whether user is resting, active, or post-workout.
        Critical for avoiding false stress positives from exercise.

        Contexts:
          resting      — normal state
          active       — currently exercising
          post_workout — elevated HR from recent exercise
          sleeping     — very low HR + low HRV (normal during sleep)
        """
        hr    = reading.heart_rate
        steps = reading.steps

        if hr is None:
            return "resting"

        # Very low HR — likely sleeping or deeply relaxed
        if hr < 55:
            return "sleeping"

        # High steps + high HR = exercise
        if steps is not None and steps > 500 and hr > 110:
            return "active"

        # High HR + confirmed low steps = post workout
        # IMPORTANT: If steps is None we cannot confirm exercise
        # so do NOT classify as post_workout — treat as resting stress
        if hr > 110 and steps is not None and steps < 200:
            return "post_workout"

        return "resting"

    # ─────────────────────────────────────────────────
    # Composite physio score
    # ─────────────────────────────────────────────────
    def _calculate_physio_score(
        self,
        hrv_score:   float,
        hr_score:    float,
        sleep_score: float,
        active:      int,
        context:     str,
        hrv_dev:     float,
        hr_dev:      float
    ) -> float:
        """
        Weighted combination of HRV, HR, and sleep scores.

        Weights:
          HRV:   55% — most reliable stress signal
          HR:    30% — good real-time indicator
          Sleep: 15% — background context

        Adjustments:
          - HRV and HR both elevated above baseline → +10 boost
          - Post-workout context → reduce HR weight
          - Sleep deprivation → amplifies other signals
        """
        if active == 0:
            return 50.0

        # Adjust weights for context
        if context == "post_workout":
            # HR unreliable post-workout — shift weight to HRV
            hrv_w, hr_w, sleep_w = 0.70, 0.15, 0.15
        elif context == "sleeping":
            # During sleep HRV is naturally lower
            hrv_w, hr_w, sleep_w = 0.40, 0.20, 0.40
        else:
            hrv_w, hr_w, sleep_w = 0.55, 0.30, 0.15

        # Calculate weighted score
        score = (
            hrv_score   * hrv_w   +
            hr_score    * hr_w    +
            sleep_score * sleep_w
        )

        # Both HRV and HR elevated above personal baseline → boost
        if hrv_dev > 20 and hr_dev > 15:
            score = min(100.0, score + 10)

        # Poor sleep amplifies stress signals
        if sleep_score > 70:
            score = min(100.0, score * 1.1)

        return max(0.0, min(100.0, score))

    # ─────────────────────────────────────────────────
    # Smoothing
    # ─────────────────────────────────────────────────
    def _smooth(self, score: float) -> float:
        """
        Weighted temporal smoothing over last 5 readings.
        Prevents single-reading spikes from spiking the ELI.
        """
        self._history.append(score)
        if len(self._history) > self._history_size:
            self._history.pop(0)

        n       = min(5, len(self._history))
        recent  = self._history[-n:]

        # Single reading — return as-is, don't dampen
        if n == 1:
            return recent[0]

        weights = [i + 1 for i in range(n)]
        total   = sum(weights)

        return sum(v * w for v, w in zip(recent, weights)) / total

    # ─────────────────────────────────────────────────
    # Baseline learning
    # ─────────────────────────────────────────────────
    def _update_baseline(self, reading: WatchReading):
        """
        Update personal baseline with new reading.
        Only updates during resting state to avoid
        exercise contaminating the baseline.
        """
        b = self._baseline

        if reading.hrv is not None:
            b["hrv_readings"].append(reading.hrv)
            if len(b["hrv_readings"]) > 100:
                b["hrv_readings"] = b["hrv_readings"][-100:]
            if len(b["hrv_readings"]) >= 5:
                b["hrv"] = statistics.median(b["hrv_readings"])

        if reading.heart_rate is not None:
            b["hr_readings"].append(reading.heart_rate)
            if len(b["hr_readings"]) > 100:
                b["hr_readings"] = b["hr_readings"][-100:]
            if len(b["hr_readings"]) >= 5:
                b["hr"] = statistics.median(b["hr_readings"])

    # ─────────────────────────────────────────────────
    # Watch source parsers
    # Each watch brand sends data in different formats.
    # These methods normalise them to WatchReading.
    # ─────────────────────────────────────────────────

    def parse_apple_watch(self, payload: dict) -> WatchReading:
        """
        Parse Apple Watch payload from Apple Shortcuts webhook.

        Apple Shortcuts automation runs every 30 seconds and
        POSTs to /api/watch/apple with this structure:

        {
            "hrv": 42.3,           // SDNN or RMSSD from Health app
            "heart_rate": 78,
            "sleep_hours": 6.5,    // from Sleep app
            "steps": 3420,
            "spo2": 98.1
        }

        Apple Shortcuts setup:
          1. Open Shortcuts app
          2. New Automation → Time of Day → Every 30 seconds
          3. Add action: Get Health Samples (HRV)
          4. Add action: Get Health Samples (Heart Rate)
          5. Add action: URL → POST to http://YOUR_IP:8000/api/watch/apple
          6. Add action: Get Contents of URL
        """
        return WatchReading(
            hrv          = self._safe_float(payload.get("hrv")),
            heart_rate   = self._safe_float(payload.get("heart_rate")
                           or payload.get("heartRate")
                           or payload.get("hr")),
            sleep_hours  = self._safe_float(payload.get("sleep_hours")
                           or payload.get("sleepHours")),
            sleep_quality= self._safe_float(payload.get("sleep_quality")),
            steps        = self._safe_float(payload.get("steps")
                           or payload.get("stepCount")),
            spo2         = self._safe_float(payload.get("spo2")
                           or payload.get("bloodOxygen")),
            source       = "apple",
        )

    def parse_samsung(self, payload: dict) -> WatchReading:
        """
        Parse Samsung Galaxy Watch / Samsung Health export.

        Samsung Health sends:
        {
            "stress_score": 65,         // Samsung's own score
            "heart_rate": 82,
            "hrv_rmssd": 38.2,
            "sleep_score": 72,
            "step_count": 2100
        }
        """
        # Samsung has its own sleep score (0-100)
        sleep_hrs = None
        if payload.get("sleep_duration_minutes"):
            sleep_hrs = payload["sleep_duration_minutes"] / 60

        return WatchReading(
            hrv          = self._safe_float(
                               payload.get("hrv_rmssd")
                               or payload.get("hrv")),
            heart_rate   = self._safe_float(payload.get("heart_rate")),
            sleep_hours  = sleep_hrs,
            sleep_quality= self._safe_float(payload.get("sleep_score")),
            steps        = self._safe_float(payload.get("step_count")
                           or payload.get("steps")),
            source       = "samsung",
        )

    def parse_fitbit(self, payload: dict) -> WatchReading:
        """
        Parse Fitbit Web API response.

        Fitbit API returns:
        {
            "activities-heart": [{"value": {"restingHeartRate": 68}}],
            "activities-heart-intraday": {...},
            "sleep": {"summary": {"totalTimeInBed": 420}}
        }
        """
        hr = None
        if "activities-heart" in payload:
            try:
                hr = payload["activities-heart"][0]["value"]["restingHeartRate"]
            except (KeyError, IndexError):
                pass

        sleep_hrs = None
        if "sleep" in payload:
            try:
                mins      = payload["sleep"]["summary"]["totalTimeInBed"]
                sleep_hrs = mins / 60
            except (KeyError, TypeError):
                pass

        return WatchReading(
            hrv        = self._safe_float(payload.get("hrv_rmssd")),
            heart_rate = self._safe_float(hr),
            sleep_hours= sleep_hrs,
            steps      = self._safe_float(
                             payload.get("summary", {}).get("steps")),
            source     = "fitbit",
        )

    def parse_generic(self, payload: dict) -> WatchReading:
        """
        Parse generic webhook payload.
        Works for Mi Band, Garmin, Whoop, any other device
        posting to /api/watch/generic

        Expected format (flexible):
        {
            "hrv": 40,
            "hr":  75,
            "sleep": 6.0,
            "steps": 1800
        }
        """
        return WatchReading(
            hrv        = self._safe_float(
                             payload.get("hrv")
                             or payload.get("hrv_rmssd")
                             or payload.get("heart_rate_variability")),
            heart_rate = self._safe_float(
                             payload.get("hr")
                             or payload.get("heart_rate")
                             or payload.get("bpm")),
            sleep_hours= self._safe_float(
                             payload.get("sleep")
                             or payload.get("sleep_hours")),
            steps      = self._safe_float(
                             payload.get("steps")
                             or payload.get("step_count")),
            source     = "generic",
        )

    # ─────────────────────────────────────────────────
    # Simulator — for demo when no watch connected
    # ─────────────────────────────────────────────────

    def get_simulated_reading(
        self,
        scenario: str = "normal"
    ) -> WatchReading:
        """
        Generate realistic simulated watch data for demo.

        Scenarios:
          normal       — baseline relaxed state
          stressed     — elevated HRV suppression + HR rise
          anxious      — high HR variability, low HRV
          tired        — poor sleep, slightly elevated HR
          escalating   — gradually worsening over time
          crisis       — extreme values → triggers crisis override

        Dev 3 uses this to drive the demo without a real watch.
        """
        import math
        import random

        self._sim_time += 1
        t = self._sim_time

        if scenario == "normal":
            return WatchReading(
                hrv          = 55 + random.gauss(0, 3),
                heart_rate   = 68 + random.gauss(0, 2),
                sleep_hours  = 7.5,
                steps        = min(8000, t * 15),
                source       = "simulated",
            )

        elif scenario == "stressed":
            # HRV drops, HR rises over time
            return WatchReading(
                hrv          = max(15, 50 - t * 0.5 + random.gauss(0, 2)),
                heart_rate   = min(105, 72 + t * 0.3 + random.gauss(0, 3)),
                sleep_hours  = 6.0,
                steps        = min(5000, t * 10),
                source       = "simulated",
            )

        elif scenario == "anxious":
            # Low HRV + fast HR + poor sleep
            return WatchReading(
                hrv          = 28 + random.gauss(0, 5),
                heart_rate   = 92 + random.gauss(0, 4),
                sleep_hours  = 5.0,
                steps        = min(3000, t * 8),
                source       = "simulated",
            )

        elif scenario == "tired":
            # Normal HR but low HRV from poor sleep
            return WatchReading(
                hrv          = 35 + random.gauss(0, 3),
                heart_rate   = 74 + random.gauss(0, 2),
                sleep_hours  = 4.5,
                sleep_quality= 45.0,
                steps        = min(4000, t * 12),
                source       = "simulated",
            )

        elif scenario == "escalating":
            # Gradually worsening — good for demo graph
            progress = min(1.0, t / 30)
            return WatchReading(
                hrv          = max(20, 60 - progress * 40
                                   + random.gauss(0, 2)),
                heart_rate   = min(100, 65 + progress * 35
                                   + random.gauss(0, 3)),
                sleep_hours  = max(4, 8 - progress * 4),
                steps        = min(6000, t * 12),
                source       = "simulated",
            )

        elif scenario == "crisis":
            # Extreme values → CRISIS_RISK in fusion engine
            return WatchReading(
                hrv          = 12 + random.gauss(0, 2),
                heart_rate   = 115 + random.gauss(0, 3),
                sleep_hours  = 3.0,
                steps        = 200,
                source       = "simulated",
            )

        return self.get_simulated_reading("normal")

    def simulate_and_process(
        self,
        scenario: str = "normal"
    ) -> PhysioResult:
        """
        Convenience method — simulate + process in one call.
        Dev 3 calls this to drive demo.
        """
        reading = self.get_simulated_reading(scenario)
        return self.process(reading)

    # ─────────────────────────────────────────────────
    # Dev 2 interface
    # ─────────────────────────────────────────────────

    @property
    def last_result(self) -> PhysioResult:
        """Thread-safe read of last processed result."""
        with self._lock:
            return self._last_result

    def to_dict(self) -> dict:
        """
        Thread-safe snapshot for FastAPI WebSocket.
        Dev 2 calls this every 3 seconds in the stream loop.
        """
        with self._lock:
            r = self._last_result
            return {
                "physio_score":     r.physio_score,
                "hrv_score":        r.hrv_score,
                "hr_score":         r.hr_score,
                "sleep_score":      r.sleep_score,
                "activity_context": r.activity_context,
                "hrv":              r.hrv,
                "heart_rate":       r.heart_rate,
                "sleep_hours":      r.sleep_hours,
                "hrv_deviation":    r.hrv_deviation,
                "hr_deviation":     r.hr_deviation,
                "active_signals":   r.active_signals,
                "confidence":       r.confidence,
                "source":           r.source,
                "timestamp":        r.timestamp,
            }

    def get_baseline_dict(self) -> dict:
        """Return current personal baseline."""
        return {
            "hrv_baseline":       round(self._baseline["hrv"], 1),
            "hr_baseline":        round(self._baseline["heart_rate"], 1),
            "hrv_data_points":    len(self._baseline["hrv_readings"]),
            "hr_data_points":     len(self._baseline["hr_readings"]),
            "is_calibrated":      len(self._baseline["hrv_readings"]) >= 5,
        }

    # ─────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert any value to float or None."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _deviation(
        self,
        current:  Optional[float],
        baseline: float
    ) -> float:
        """Percentage deviation from baseline."""
        if current is None or baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100


# ─────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────
watch_analyzer = WatchAnalyzer()