# services/ml/fusion_engine.py
#
# Emotional Load Index (ELI) Fusion Engine
# Combines 4 independent signals into a single unified score.
#
# Signal weights:
#   Physiological (watch) → 40%
#   Facial emotion        → 30%
#   Voice + transcript    → 20%
#   Typing pattern        → 10%
#
# Special rules:
#   Missing signals    → weights redistributed proportionally
#   Signal conflict    → MASKING_DETECTED (disagreement > 40 pts)
#   Any signal > 85    → CRISIS_RISK override
#   Contradiction flag → boosts ELI by 10 points

from dataclasses import dataclass, field
from typing import Optional
import time


# ─────────────────────────────────────────────────────
# Input / Output data classes
# ─────────────────────────────────────────────────────

@dataclass
class SignalInput:
    """
    All 4 input signals for the fusion engine.
    Any signal can be None if unavailable.
    """
    physio_score:          Optional[float] = None   # 0–100 from watch
    facial_score:          Optional[float] = None   # 0–100 from facial_analysis
    voice_score:           Optional[float] = None   # 0–100 combined_score from voice_analysis
    typing_score:          Optional[float] = None   # 0–100 from React frontend

    # Optional enrichment from voice module
    contradiction_detected: bool = False             # words vs voice mismatch
    contradiction_type:     str  = "none"            # masking / suppression / CRISIS
    transcript:             str  = ""                # what user said
    facial_emotion:         str  = "neutral"         # dominant facial emotion
    voice_emotion:          str  = "neutral"         # dominant voice emotion


@dataclass
class ELIResult:
    """
    Full output from the fusion engine.
    Dev 2 sends this directly to the React frontend via WebSocket.
    """
    # Core score
    eli:            float           # 0–100 Emotional Load Index
    eli_label:      str             # calm / moderate / elevated / high / critical

    # Status flags
    status:         str             # NORMAL | MASKING_DETECTED | CRISIS_RISK | NO_SIGNAL

    # Signal breakdown — for explainability panel
    breakdown:      dict            # per-signal scores and contributions
    active_signals: int             # how many signals are active
    confidence:     float           # 0–100 based on active signals

    # Dominant emotion across all signals
    dominant_emotion: str           # fused emotion from face + voice

    # Flags passed through for therapy agent
    contradiction_detected: bool
    contradiction_type:     str
    transcript:             str

    # History for trend tracking
    eli_trend:      str             # rising / falling / stable

    timestamp:      float = field(default_factory=time.time)


# ─────────────────────────────────────────────────────
# Fusion Engine
# ─────────────────────────────────────────────────────

class FusionEngine:
    """
    Combines 4 independent emotional signals into the
    Emotional Load Index (ELI).

    Design principles:
    - Personal baseline deviation > raw scores
    - Signal conflict is itself a clinical signal (masking)
    - Crisis override ignores weighted average
    - Graceful degradation when signals are missing
    """

    # Base weights — must sum to 1.0
    BASE_WEIGHTS = {
        'physio': 0.40,
        'facial': 0.30,
        'voice':  0.20,
        'typing': 0.10,
    }

    # Thresholds
    CRISIS_THRESHOLD  = 85.0    # any single signal above this → crisis
    MASKING_THRESHOLD = 50.0    # signal spread above this → masking
    CONTRADICTION_BOOST = 10.0  # add to ELI when contradiction detected

    # ELI label ranges
    ELI_LABELS = [
        (0,   20,  "calm"),
        (20,  40,  "low"),
        (40,  60,  "moderate"),
        (60,  75,  "elevated"),
        (75,  88,  "high"),
        (88,  101, "critical"),
    ]

    def __init__(self):
        self._eli_history = []     # last 10 ELI values for trend
        self._history_max = 10

    # ─────────────────────────────────────────────────
    # Primary method — call this every 3 seconds
    # ─────────────────────────────────────────────────
    def calculate(self, signals: SignalInput) -> ELIResult:
        """
        Calculate ELI from all available signals.
        Always returns a result — handles missing signals gracefully.
        """

        # 1. Collect active signals
        raw = {
            'physio': signals.physio_score,
            'facial': signals.facial_score,
            'voice':  signals.voice_score,
            'typing': signals.typing_score,
        }
        active = {k: v for k, v in raw.items() if v is not None}

        # 2. Handle no signal case
        if not active:
            return self._no_signal_result()

        # 3. Redistribute weights for missing signals
        weights = self._redistribute_weights(active.keys())

        # 4. Calculate weighted ELI
        eli = sum(weights[k] * v for k, v in active.items())

        # 5. Confidence score
        confidence = (len(active) / 4) * 100

        # 6. Determine status
        status = self._determine_status(
            eli,
            list(active.values()),
            signals.contradiction_detected,
            signals.contradiction_type
        )

        # 7. Boost ELI if contradiction detected
        if signals.contradiction_detected and status != "CRISIS_RISK":
            eli = min(100.0, eli + self.CONTRADICTION_BOOST)

        # 8. Build breakdown for explainability panel
        breakdown = self._build_breakdown(active, weights)

        # 9. ELI label
        eli_label = self._get_label(eli)

        # 10. Fuse dominant emotion from face + voice
        dominant_emotion = self._fuse_emotion(
            signals.facial_emotion,
            signals.voice_emotion,
            active
        )

        # 11. Trend detection
        eli_trend = self._calculate_trend(eli)

        return ELIResult(
            eli=round(eli, 1),
            eli_label=eli_label,
            status=status,
            breakdown=breakdown,
            active_signals=len(active),
            confidence=round(confidence, 1),
            dominant_emotion=dominant_emotion,
            contradiction_detected=signals.contradiction_detected,
            contradiction_type=signals.contradiction_type,
            transcript=signals.transcript,
            eli_trend=eli_trend,
        )

    # ─────────────────────────────────────────────────
    # Status determination
    # ─────────────────────────────────────────────────
    def _determine_status(
        self,
        eli:                    float,
        scores:                 list,
        contradiction_detected: bool,
        contradiction_type:     str
    ) -> str:
        """
        Determine system status from signals.

        Priority order:
        1. CRISIS_RISK     — any single signal > 85 or crisis language
        2. MASKING_DETECTED — signals disagree by > 40 points
        3. NORMAL          — everything within expected range
        """

        # Crisis override — highest priority
        if any(s > self.CRISIS_THRESHOLD for s in scores):
            return "CRISIS_RISK"

        if contradiction_type == "CRISIS":
            return "CRISIS_RISK"

        # Masking detection — signal conflict
        if len(scores) >= 2:
            spread = max(scores) - min(scores)
            if spread > self.MASKING_THRESHOLD:
                return "MASKING_DETECTED"

        # Contradiction also indicates masking
        if contradiction_detected and contradiction_type == "masking":
            return "MASKING_DETECTED"

        return "NORMAL"

    # ─────────────────────────────────────────────────
    # Weight redistribution
    # ─────────────────────────────────────────────────
    def _redistribute_weights(self, active_keys) -> dict:
        """
        Proportionally redistribute weights from missing signals
        to active signals.

        Example — if voice is missing:
          physio: 0.40 → 0.40/0.90 = 0.444
          facial: 0.30 → 0.30/0.90 = 0.333
          typing: 0.10 → 0.10/0.90 = 0.111 (+ rounding)
          voice:  missing → 0
        """
        active_weight_sum = sum(
            self.BASE_WEIGHTS[k] for k in active_keys
        )

        return {
            k: self.BASE_WEIGHTS[k] / active_weight_sum
            for k in active_keys
        }

    # ─────────────────────────────────────────────────
    # Breakdown for explainability panel
    # ─────────────────────────────────────────────────
    def _build_breakdown(self, active: dict, weights: dict) -> dict:
        """
        Build per-signal breakdown for the React explainability panel.
        Shows judges exactly how ELI was calculated.
        """
        breakdown = {}

        signal_labels = {
            'physio': 'Physiological (Watch)',
            'facial': 'Facial Emotion',
            'voice':  'Voice + Speech',
            'typing': 'Typing Pattern',
        }

        for key, score in active.items():
            weight      = weights[key]
            contribution = weight * score

            breakdown[key] = {
                "label":        signal_labels[key],
                "score":        round(score, 1),
                "weight_pct":   round(weight * 100, 1),
                "contribution": round(contribution, 1),
                "active":       True,
            }

        # Mark missing signals
        for key in self.BASE_WEIGHTS:
            if key not in active:
                breakdown[key] = {
                    "label":        signal_labels[key],
                    "score":        None,
                    "weight_pct":   0,
                    "contribution": 0,
                    "active":       False,
                }

        return breakdown

    # ─────────────────────────────────────────────────
    # Emotion fusion
    # ─────────────────────────────────────────────────
    def _fuse_emotion(
        self,
        facial_emotion: str,
        voice_emotion:  str,
        active:         dict
    ) -> str:
        """
        Fuse dominant emotion from face and voice signals.
        Voice gets priority if physiological score is high.
        Face gets priority if voice is unavailable.
        """
        if not facial_emotion or facial_emotion == "neutral":
            return voice_emotion or "neutral"

        if not voice_emotion or voice_emotion == "neutral":
            return facial_emotion or "neutral"

        # Both available — use voice if physio is elevated
        # (voice is harder to fake under stress)
        physio = active.get('physio', 50)
        if physio > 65:
            return voice_emotion

        # Both agree — trust it
        if facial_emotion == voice_emotion:
            return facial_emotion

        # Disagreement — use emotion with higher distress weight
        distress_priority = ["fear", "angry", "sad", "disgust",
                             "surprise", "happy", "neutral"]

        facial_idx = distress_priority.index(facial_emotion) \
            if facial_emotion in distress_priority else 99
        voice_idx  = distress_priority.index(voice_emotion)  \
            if voice_emotion  in distress_priority else 99

        return facial_emotion if facial_idx < voice_idx else voice_emotion

    # ─────────────────────────────────────────────────
    # Trend detection
    # ─────────────────────────────────────────────────
    def _calculate_trend(self, current_eli: float) -> str:
        """
        Detect if ELI is rising, falling, or stable.
        Uses last 5 readings.
        """
        self._eli_history.append(current_eli)
        if len(self._eli_history) > self._history_max:
            self._eli_history.pop(0)

        if len(self._eli_history) < 3:
            return "stable"

        recent = self._eli_history[-5:]
        first  = sum(recent[:2])  / 2
        last   = sum(recent[-2:]) / 2
        diff   = last - first

        if diff > 8:
            return "rising"
        elif diff < -8:
            return "falling"
        return "stable"

    # ─────────────────────────────────────────────────
    # ELI label
    # ─────────────────────────────────────────────────
    def _get_label(self, eli: float) -> str:
        for low, high, label in self.ELI_LABELS:
            if low <= eli < high:
                return label
        return "critical"

    # ─────────────────────────────────────────────────
    # No signal fallback
    # ─────────────────────────────────────────────────
    def _no_signal_result(self) -> ELIResult:
        return ELIResult(
            eli=50.0,
            eli_label="moderate",
            status="NO_SIGNAL",
            breakdown={},
            active_signals=0,
            confidence=0.0,
            dominant_emotion="neutral",
            contradiction_detected=False,
            contradiction_type="none",
            transcript="",
            eli_trend="stable",
        )

    # ─────────────────────────────────────────────────
    # Dev 2 interface
    # ─────────────────────────────────────────────────
    def to_dict(self, result: ELIResult) -> dict:
        """
        Convert ELIResult to dict for WebSocket transmission.
        Dev 2 sends this directly to React frontend.
        """
        return {
            "eli":                   result.eli,
            "eli_label":             result.eli_label,
            "status":                result.status,
            "breakdown":             result.breakdown,
            "active_signals":        result.active_signals,
            "confidence":            result.confidence,
            "dominant_emotion":      result.dominant_emotion,
            "contradiction_detected":result.contradiction_detected,
            "contradiction_type":    result.contradiction_type,
            "transcript":            result.transcript,
            "eli_trend":             result.eli_trend,
            "timestamp":             result.timestamp,
        }


# ─────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────
fusion_engine = FusionEngine()