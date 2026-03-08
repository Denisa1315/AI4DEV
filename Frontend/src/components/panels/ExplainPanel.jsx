import useAppStore from "../../store/useAppStore"
import { getEliColor } from "../../utils/scoring"

export default function ExplainPanel() {
  const eliData   = useAppStore((s) => s.eliData)
  const watchData = useAppStore((s) => s.watchData)
  const eli       = eliData?.eli       ?? 50
  const breakdown = eliData?.breakdown ?? {}
  const status    = eliData?.status    ?? "NORMAL"
  const color     = getEliColor(eli)

  const reasons = []
  if (watchData?.hrv && watchData.hrv < 40)
    reasons.push(`HRV ${watchData.hrv}ms — below your baseline`)
  if (watchData?.heart_rate && watchData.heart_rate > 85)
    reasons.push(`Heart rate elevated at ${watchData.heart_rate} bpm`)
  if (breakdown.facial?.score > 55)
    reasons.push(`Facial distress at ${Math.round(breakdown.facial.score)} — ${eliData?.dominant_emotion} detected`)
  if (breakdown.voice?.score > 55)
    reasons.push(`Voice stress score: ${Math.round(breakdown.voice.score)}`)
  if (breakdown.typing?.score > 55)
    reasons.push(`Typing pattern shows cognitive strain`)
  if (status === "MASKING_DETECTED")
    reasons.push("Contradiction: verbal calm ≠ physiological stress")
  if (reasons.length === 0) {
    reasons.push("All signals within normal range")
    reasons.push(`Confidence: ${eliData?.confidence ?? 70}%`)
  }

  return (
    <div className="glass rounded-2xl p-4 flex-1">
      <p className="text-gray-500 text-xs tracking-widest uppercase mb-3">Why this score?</p>
      <div className="space-y-2">
        {reasons.map((r, i) => (
          <div key={i} className="flex items-start gap-2 text-xs">
            <span className="mt-0.5 shrink-0" style={{ color }}>›</span>
            <span className="text-gray-400 leading-relaxed">{r}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-gray-800/60">
        <p className="text-gray-600 text-xs">
          {eli > 85 ? "Crisis protocol active — iCall helpline suggested"
            : eli > 65 ? "Active support mode — grounding or CBT engaged"
            : eli > 40 ? "Gentle check-in mode — validating your experience"
            : "Calm mode — open conversation"}
        </p>
      </div>
    </div>
  )
}