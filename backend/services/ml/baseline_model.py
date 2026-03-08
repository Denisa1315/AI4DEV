# services/ml/baseline_model.py
#
# Personal Emotional Baseline Model for Emora.
#
# Instead of comparing user scores against population averages,
# this model learns each user's personal normal ranges over time.
#
# Deviation from personal baseline is far more meaningful
# than raw scores — a score of 70 means nothing without knowing
# that this user's normal is 40.
#
# Storage: MongoDB (via Dev 2's database connection)
# Fallback: In-memory store for POC demo

import time
import statistics
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────

@dataclass
class UserBaseline:
    """
    Personal baseline for a single user.
    Built from their first N sessions.
    """
    user_id:       str

    # Physiological baselines
    hrv_baseline:       float = 55.0    # ms
    hr_baseline:        float = 72.0    # bpm
    physio_baseline:    float = 50.0    # score

    # Facial baselines
    facial_baseline:    float = 30.0    # distress score
    neutral_confidence: float = 80.0    # how often neutral is detected

    # Voice baselines
    pitch_baseline:     float = 150.0   # Hz
    energy_baseline:    float = 0.05
    rate_baseline:      float = 4.0     # syllables/sec
    voice_baseline:     float = 45.0    # stress score

    # ELI baseline
    eli_baseline:       float = 50.0
    eli_std:            float = 10.0    # normal variation range

    # Metadata
    data_points:        int   = 0
    is_calibrated:      bool  = False   # True after 5+ sessions
    created_at:         float = field(default_factory=time.time)
    updated_at:         float = field(default_factory=time.time)


@dataclass
class DeviationResult:
    """
    How much current readings deviate from personal baseline.
    Positive = above baseline (more stressed than usual)
    Negative = below baseline (calmer than usual)
    """
    physio_deviation:   float   # percentage deviation
    facial_deviation:   float
    voice_deviation:    float
    eli_deviation:      float

    # Is this significantly above normal?
    physio_elevated:    bool
    facial_elevated:    bool
    voice_elevated:     bool
    eli_elevated:       bool

    # Context message for therapy agent
    context_message:    str
    is_calibrated:      bool


# ─────────────────────────────────────────────────────
# Baseline Model
# ─────────────────────────────────────────────────────

class BaselineModel:
    """
    Learns and stores personal emotional baselines per user.

    For POC: uses in-memory storage
    For production: Dev 2 connects this to MongoDB

    The model uses a rolling median (not mean) to resist
    outliers — one panic attack shouldn't shift the baseline.
    """

    # Minimum readings before baseline is considered calibrated
    CALIBRATION_THRESHOLD = 5

    # How many readings to keep per signal
    MAX_HISTORY = 100

    # Deviation threshold — above this = "elevated"
    ELEVATION_THRESHOLD = 25.0   # percentage

    def __init__(self):
        # In-memory store: user_id → UserBaseline
        self._baselines: dict[str, UserBaseline] = {}

        # History store: user_id → signal histories
        self._histories: dict[str, dict] = {}

        # Default user for POC (single user demo)
        self._demo_user_id = "demo_user"
        self._init_user(self._demo_user_id)

        print("[BaselineModel] Ready ✓")

    # ─────────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────────
    def _init_user(self, user_id: str):
        """Create baseline entry for new user."""
        if user_id not in self._baselines:
            self._baselines[user_id] = UserBaseline(user_id=user_id)
            self._histories[user_id] = {
                "physio":  [],
                "facial":  [],
                "voice":   [],
                "eli":     [],
                "hrv":     [],
                "hr":      [],
                "pitch":   [],
                "energy":  [],
            }

    # ─────────────────────────────────────────────────
    # Update baseline with new readings
    # ─────────────────────────────────────────────────
    def update(
        self,
        user_id:      str,
        physio_score: Optional[float] = None,
        facial_score: Optional[float] = None,
        voice_score:  Optional[float] = None,
        eli:          Optional[float] = None,
        hrv:          Optional[float] = None,
        hr:           Optional[float] = None,
        pitch:        Optional[float] = None,
        energy:       Optional[float] = None,
    ):
        """
        Add new readings to baseline history.
        Call this every time a new ELI is calculated.
        Baseline updates automatically once enough data exists.
        """
        if user_id not in self._baselines:
            self._init_user(user_id)

        h = self._histories[user_id]
        b = self._baselines[user_id]

        # Append to histories
        if physio_score is not None:
            h["physio"].append(physio_score)
        if facial_score is not None:
            h["facial"].append(facial_score)
        if voice_score is not None:
            h["voice"].append(voice_score)
        if eli is not None:
            h["eli"].append(eli)
        if hrv is not None:
            h["hrv"].append(hrv)
        if hr is not None:
            h["hr"].append(hr)
        if pitch is not None:
            h["pitch"].append(pitch)
        if energy is not None:
            h["energy"].append(energy)

        # Trim to max history length
        for key in h:
            if len(h[key]) > self.MAX_HISTORY:
                h[key] = h[key][-self.MAX_HISTORY:]

        # Recalculate baselines
        self._recalculate(user_id)

        # Update metadata
        b.data_points += 1
        b.updated_at   = time.time()
        b.is_calibrated = b.data_points >= self.CALIBRATION_THRESHOLD

    def _recalculate(self, user_id: str):
        """Recalculate baseline medians from history."""
        h = self._histories[user_id]
        b = self._baselines[user_id]

        if len(h["physio"])  >= 3:
            b.physio_baseline = self._median(h["physio"])
        if len(h["facial"])  >= 3:
            b.facial_baseline = self._median(h["facial"])
        if len(h["voice"])   >= 3:
            b.voice_baseline  = self._median(h["voice"])
        if len(h["eli"])     >= 3:
            b.eli_baseline    = self._median(h["eli"])
            b.eli_std         = self._std(h["eli"])
        if len(h["hrv"])     >= 3:
            b.hrv_baseline    = self._median(h["hrv"])
        if len(h["hr"])      >= 3:
            b.hr_baseline     = self._median(h["hr"])
        if len(h["pitch"])   >= 3:
            b.pitch_baseline  = self._median(h["pitch"])
        if len(h["energy"])  >= 3:
            b.energy_baseline = self._median(h["energy"])

    # ─────────────────────────────────────────────────
    # Get deviation from baseline
    # ─────────────────────────────────────────────────
    def get_deviation(
        self,
        user_id:      str,
        physio_score: Optional[float] = None,
        facial_score: Optional[float] = None,
        voice_score:  Optional[float] = None,
        eli:          Optional[float] = None,
    ) -> DeviationResult:
        """
        Calculate how much current readings deviate from baseline.
        Used by therapy agent to contextualise current state.
        """
        if user_id not in self._baselines:
            self._init_user(user_id)

        b = self._baselines[user_id]

        physio_dev = self._pct_deviation(physio_score, b.physio_baseline)
        facial_dev = self._pct_deviation(facial_score, b.facial_baseline)
        voice_dev  = self._pct_deviation(voice_score,  b.voice_baseline)
        eli_dev    = self._pct_deviation(eli,           b.eli_baseline)

        physio_elevated = physio_dev > self.ELEVATION_THRESHOLD
        facial_elevated = facial_dev > self.ELEVATION_THRESHOLD
        voice_elevated  = voice_dev  > self.ELEVATION_THRESHOLD
        eli_elevated    = eli_dev    > self.ELEVATION_THRESHOLD

        context = self._build_context_message(
            b, eli, eli_dev,
            physio_elevated, facial_elevated, voice_elevated
        )

        return DeviationResult(
            physio_deviation=round(physio_dev, 1),
            facial_deviation=round(facial_dev, 1),
            voice_deviation= round(voice_dev,  1),
            eli_deviation=   round(eli_dev,    1),
            physio_elevated=physio_elevated,
            facial_elevated=facial_elevated,
            voice_elevated= voice_elevated,
            eli_elevated=   eli_elevated,
            context_message=context,
            is_calibrated=  b.is_calibrated,
        )

    # ─────────────────────────────────────────────────
    # Context message for therapy agent
    # ─────────────────────────────────────────────────
    def _build_context_message(
        self,
        baseline:          UserBaseline,
        current_eli:       Optional[float],
        eli_deviation:     float,
        physio_elevated:   bool,
        facial_elevated:   bool,
        voice_elevated:    bool,
    ) -> str:
        """
        Generate a plain-language context string for the
        LangChain therapy agent's system prompt.

        Example output:
        "User's ELI is 34% above their personal baseline.
         Both physiological and facial signals are elevated.
         This is significantly higher than their normal range."
        """
        if not baseline.is_calibrated:
            return "Baseline not yet calibrated — using population defaults."

        parts = []

        if current_eli is not None:
            if eli_deviation > 30:
                parts.append(
                    f"User's stress is {eli_deviation:.0f}% above their "
                    f"personal baseline (their normal is around "
                    f"{baseline.eli_baseline:.0f}/100)."
                )
            elif eli_deviation < -20:
                parts.append(
                    f"User appears calmer than usual — "
                    f"{abs(eli_deviation):.0f}% below their baseline."
                )
            else:
                parts.append(
                    f"User's stress is within their normal range "
                    f"(baseline: {baseline.eli_baseline:.0f}/100)."
                )

        elevated = []
        if physio_elevated: elevated.append("physiological")
        if facial_elevated: elevated.append("facial")
        if voice_elevated:  elevated.append("voice")

        if len(elevated) >= 2:
            parts.append(
                f"Multiple signals elevated: {', '.join(elevated)}."
            )
        elif len(elevated) == 1:
            parts.append(f"{elevated[0].capitalize()} signal elevated.")

        return " ".join(parts) if parts else "Normal baseline state."

    # ─────────────────────────────────────────────────
    # Get baseline for a user
    # ─────────────────────────────────────────────────
    def get_baseline(self, user_id: str) -> UserBaseline:
        if user_id not in self._baselines:
            self._init_user(user_id)
        return self._baselines[user_id]

    def get_baseline_dict(self, user_id: str) -> dict:
        """Return baseline as dict for API response."""
        b = self.get_baseline(user_id)
        return {
            "user_id":        b.user_id,
            "physio_baseline":b.physio_baseline,
            "facial_baseline":b.facial_baseline,
            "voice_baseline": b.voice_baseline,
            "eli_baseline":   b.eli_baseline,
            "eli_std":        b.eli_std,
            "hrv_baseline":   b.hrv_baseline,
            "hr_baseline":    b.hr_baseline,
            "data_points":    b.data_points,
            "is_calibrated":  b.is_calibrated,
        }

    # ─────────────────────────────────────────────────
    # Session opening intelligence
    # ─────────────────────────────────────────────────
    def get_session_opening_context(
        self,
        user_id:         str,
        current_eli:     float,
        current_hrv:     Optional[float] = None,
        sleep_hours:     Optional[float] = None,
        day_of_week:     Optional[str]   = None,
    ) -> str:
        """
        Generate personalised session opening message context.
        Used by Dev 2's session opening intelligence feature.

        Returns a string the LangChain agent uses to open the
        session with context-aware awareness.

        Example:
        "User slept 1.5h less than usual. HRV is 28% below
         baseline. Historically Mondays are their highest
         stress day. Open gently."
        """
        if user_id not in self._baselines:
            self._init_user(user_id)

        b     = self._baselines[user_id]
        parts = []

        # HRV context
        if current_hrv is not None and b.is_calibrated:
            hrv_dev = self._pct_deviation(current_hrv, b.hrv_baseline)
            if hrv_dev < -20:
                parts.append(
                    f"HRV is {abs(hrv_dev):.0f}% below their baseline "
                    f"({current_hrv:.0f}ms vs normal {b.hrv_baseline:.0f}ms)."
                )
            elif hrv_dev > 15:
                parts.append(
                    f"HRV is good today — {hrv_dev:.0f}% above baseline."
                )

        # Sleep context
        if sleep_hours is not None:
            if sleep_hours < 6.0:
                parts.append(
                    f"Only {sleep_hours:.1f}h sleep last night — "
                    f"below recommended 7-8h."
                )
            elif sleep_hours >= 7.5:
                parts.append(f"Good sleep last night ({sleep_hours:.1f}h).")

        # ELI context
        if b.is_calibrated:
            eli_dev = self._pct_deviation(current_eli, b.eli_baseline)
            if eli_dev > 25:
                parts.append(
                    f"Starting session {eli_dev:.0f}% above their "
                    f"personal stress baseline — open gently."
                )

        # Day of week context
        if day_of_week:
            high_stress_days = self._get_high_stress_days(user_id)
            if day_of_week.lower() in high_stress_days:
                parts.append(
                    f"{day_of_week} is historically a higher-stress "
                    f"day for this user."
                )

        if not parts:
            return "User appears to be in their normal baseline state."

        return " ".join(parts)

    def _get_high_stress_days(self, user_id: str) -> list:
        """
        Placeholder — in production this analyses historical
        ELI data by day of week to find patterns.
        For POC returns common high-stress days.
        """
        return ["monday", "sunday"]

    # ─────────────────────────────────────────────────
    # MongoDB sync — Dev 2 hooks into these
    # ─────────────────────────────────────────────────
    def load_from_db(self, user_id: str, db_doc: dict):
        """
        Load baseline from MongoDB document.
        Dev 2 calls this on user login.
        """
        if user_id not in self._baselines:
            self._init_user(user_id)

        b = self._baselines[user_id]

        b.physio_baseline  = db_doc.get("physio_baseline",  50.0)
        b.facial_baseline  = db_doc.get("facial_baseline",  30.0)
        b.voice_baseline   = db_doc.get("voice_baseline",   45.0)
        b.eli_baseline     = db_doc.get("eli_baseline",     50.0)
        b.eli_std          = db_doc.get("eli_std",          10.0)
        b.hrv_baseline     = db_doc.get("hrv_baseline",     55.0)
        b.hr_baseline      = db_doc.get("hr_baseline",      72.0)
        b.pitch_baseline   = db_doc.get("pitch_baseline",  150.0)
        b.energy_baseline  = db_doc.get("energy_baseline",  0.05)
        b.data_points      = db_doc.get("data_points",         0)
        b.is_calibrated    = db_doc.get("is_calibrated",   False)

        print(f"[BaselineModel] Loaded baseline for {user_id} ✓")

    def to_db_doc(self, user_id: str) -> dict:
        """
        Export baseline as MongoDB document.
        Dev 2 calls this to save after each session.
        """
        return self.get_baseline_dict(user_id)

    # ─────────────────────────────────────────────────
    # Utility helpers
    # ─────────────────────────────────────────────────
    def _pct_deviation(
        self,
        current:  Optional[float],
        baseline: float
    ) -> float:
        """Percentage deviation from baseline."""
        if current is None or baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100

    def _median(self, values: list) -> float:
        if not values:
            return 50.0
        return round(statistics.median(values), 2)

    def _std(self, values: list) -> float:
        if len(values) < 2:
            return 10.0
        return round(statistics.stdev(values), 2)


# ─────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────
baseline_model = BaselineModel()