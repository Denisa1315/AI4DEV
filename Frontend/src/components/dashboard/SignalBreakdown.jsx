import useAppStore from "../../store/useAppStore"
import { getEliColor } from "../../utils/scoring"

const SIGNALS = [
  { key: "physio", label: "Physio", icon: "💓", desc: "HRV + Heart Rate" },
  { key: "facial", label: "Facial", icon: "👁️", desc: "Webcam Emotion"  },
  { key: "voice",  label: "Voice",  icon: "🎙️", desc: "Mic Analysis"   },
  { key: "typing", label: "Typing", icon: "⌨️", desc: "Keystrokes"     },
]

export default function SignalBreakdown() {
  const eliData     = useAppStore((s) => s.eliData)
  const voiceScore  = useAppStore((s) => s.voiceScore)
  const typingScore = useAppStore((s) => s.typingScore)
  const breakdown   = eliData?.breakdown ?? {}

  const scores = {
    physio: breakdown.physio?.score ?? 50,
    facial: breakdown.facial?.score ?? 50,
    voice:  breakdown.voice?.score  ?? voiceScore,
    typing: breakdown.typing?.score ?? typingScore,
  }

  return (
    <div className="glass rounded-2xl p-4">
      <p className="text-gray-500 text-xs tracking-widest uppercase mb-4">Signal Breakdown</p>
      <div className="space-y-3">
        {SIGNALS.map(({ key, label, icon, desc }) => {
          const score = scores[key]
          const color = getEliColor(score)
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm">{icon}</span>
                  <span className="text-xs text-gray-300">{label}</span>
                  <span className="text-xs text-gray-600">{desc}</span>
                </div>
                <span className="text-xs font-mono" style={{ color }}>{Math.round(score)}</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-1.5">
                <div className="h-1.5 rounded-full transition-all duration-700"
                  style={{ width: `${score}%`, background: color, boxShadow: `0 0 6px ${color}60` }} />
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-4 pt-3 border-t border-gray-800/60">
        <p className="text-gray-700 text-xs text-center">
          Weights: Physio 40% · Facial 30% · Voice 20% · Typing 10%
        </p>
      </div>
    </div>
  )
}