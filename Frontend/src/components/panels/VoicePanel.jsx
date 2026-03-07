import useAppStore from "../../store/useAppStore"
import { getEliColor } from "../../utils/scoring"

export default function VoicePanel() {
  const voiceData   = useAppStore((s) => s.voiceData)
  const voiceScore  = useAppStore((s) => s.voiceScore)
  const isRecording = useAppStore((s) => s.isRecording)

  const score      = voiceData?.combined_score ?? voiceScore
  const transcript = voiceData?.transcript ?? ""
  const emotion    = voiceData?.dominant_emotion ?? "neutral"
  const masking    = voiceData?.contradiction_detected ?? false
  const color      = getEliColor(score)

  return (
    <div className="glass rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-gray-500 text-xs tracking-widest uppercase">Voice</p>
        <div className="flex items-center gap-1.5">
          {isRecording ? (
            <>
              <div className="flex items-end gap-0.5 h-4">
                {[1,2,3,4,5,6,7].map((_, i) => (
                  <div key={i} className="wave-bar w-0.5 bg-red-400 rounded-full" style={{ height: "100%" }} />
                ))}
              </div>
              <span className="text-red-400 text-xs">Live</span>
            </>
          ) : (
            <span className="text-gray-700 text-xs">Off</span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 mb-3">
        <div className="text-3xl font-mono font-bold" style={{ color }}>{Math.round(score)}</div>
        <div>
          <p className="text-xs text-gray-400 capitalize">{emotion}</p>
          {masking && <p className="text-xs text-orange-400">⚠️ Masking</p>}
        </div>
      </div>

      <div className="w-full bg-gray-800 rounded-full h-1.5 mb-3">
        <div className="h-1.5 rounded-full transition-all duration-700"
          style={{ width: `${score}%`, background: color }} />
      </div>

      {transcript && (
        <p className="text-gray-600 text-xs italic line-clamp-2">"{transcript}"</p>
      )}
    </div>
  )
}