import { ELI_THRESHOLDS, ELI_COLORS } from "../constants"

export function getEliColor(score) {
  if (score < ELI_THRESHOLDS.CALM) return ELI_COLORS.CALM
  if (score < ELI_THRESHOLDS.MILD) return ELI_COLORS.MILD
  if (score < ELI_THRESHOLDS.HIGH) return ELI_COLORS.HIGH
  return ELI_COLORS.CRISIS
}

export function getEliLabel(score) {
  if (score < ELI_THRESHOLDS.CALM) return "Calm"
  if (score < ELI_THRESHOLDS.MILD) return "Mild Load"
  if (score < ELI_THRESHOLDS.HIGH) return "High Load"
  return "Critical"
}

export function getStatusLabel(status) {
  const map = {
    NORMAL:           "● Live",
    MASKING_DETECTED: "⚠️ Masking Detected",
    CRISIS_RISK:      "🚨 High Risk",
    NO_SIGNAL:        "○ No Signal",
  }
  return map[status] || "● Live"
}

export function getEmotionEmoji(emotion) {
  const map = {
    sad:      "😔",
    fear:     "😨",
    angry:    "😠",
    happy:    "😊",
    neutral:  "😐",
    surprise: "😲",
    disgust:  "😒",
    contempt: "😤",
  }
  return map[emotion] || "😐"
}

export function getEmotionColor(emotion) {
  const map = {
    sad:      "#60A5FA",
    fear:     "#A78BFA",
    angry:    "#F87171",
    happy:    "#34D399",
    neutral:  "#9CA3AF",
    surprise: "#FBBF24",
    disgust:  "#F97316",
    contempt: "#FB923C",
  }
  return map[emotion] || "#9CA3AF"
}

export function predictEliLocally({ facialEmotions, voiceScore, typingScore, watchScore }) {
  const distressEmotions = ["sad", "fear", "angry", "disgust", "contempt"]
  let facialDistress = 0

  if (facialEmotions) {
    distressEmotions.forEach(e => {
      facialDistress += (facialEmotions[e] || 0) * 100
    })
    facialDistress -= (facialEmotions.happy || 0) * 30
    facialDistress = Math.max(0, Math.min(100, facialDistress))
  }

  const weights = { physio: 0.4, facial: 0.3, voice: 0.2, typing: 0.1 }
  const scores  = {
    physio: watchScore    ?? 50,
    facial: facialDistress || 50,
    voice:  voiceScore    ?? 50,
    typing: typingScore   ?? 50,
  }

  const eli = Object.keys(weights).reduce(
    (sum, k) => sum + weights[k] * scores[k], 0
  )

  return Math.round(Math.min(100, Math.max(0, eli)))
}