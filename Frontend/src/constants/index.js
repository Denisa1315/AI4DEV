export const ELI_THRESHOLDS = {
  CALM:   40,
  MILD:   65,
  HIGH:   85,
}

export const ELI_COLORS = {
  CALM:   "#22c55e",
  MILD:   "#f59e0b",
  HIGH:   "#f97316",
  CRISIS: "#ef4444",
}

export const THERAPY_MODE_LABELS = {
  grounding:  "Grounding",
  cbt:        "CBT Socratic",
  validation: "Validation",
  crisis:     "Crisis Support",
  supportive: "Supportive",
}

export const THERAPY_MODE_COLORS = {
  grounding:  "#60A5FA",
  cbt:        "#A78BFA",
  validation: "#34D399",
  crisis:     "#EF4444",
  supportive: "#F9FAFB",
}

export const WS_URL  = process.env.REACT_APP_WS_URL  || "ws://localhost:8000/ws/eli"
export const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000"

export const MOCK_WS_DATA = {
  eli: {
    eli:                    52.4,
    status:                 "NORMAL",
    confidence:             75,
    dominant_emotion:       "neutral",
    breakdown: {
      physio: { score: 58, weight: 40, contribution: 23.2 },
      facial: { score: 50, weight: 30, contribution: 15.0 },
      voice:  { score: 48, weight: 20, contribution: 9.6  },
      typing: { score: 45, weight: 10, contribution: 4.5  },
    },
    contradiction_detected: false,
    contradiction_type:     "none",
    transcript:             "",
    context_message:        "Good morning. Your HRV looks stable today.",
  },
  watch: {
    heart_rate:   72,
    hrv:          55,
    physio_score: 50,
    sleep_hours:  7.2,
    source:       "simulated",
    is_real_data: false,
  },
  facial: {
    distress_score:   50,
    dominant_emotion: "neutral",
    face_detected:    true,
    confidence:       80,
    emotions: {
      sad:      0.05,
      fear:     0.08,
      angry:    0.04,
      happy:    0.12,
      neutral:  0.65,
      surprise: 0.04,
      disgust:  0.02,
    }
  },
  voice: {
    combined_score:         48,
    voice_stress_score:     46,
    text_sentiment_score:   55,
    dominant_emotion:       "neutral",
    transcript:             "",
    transcript_sentiment:   "neutral",
    contradiction_detected: false,
    contradiction_type:     "none",
    speech_detected:        false,
    confidence:             0,
  }
}