import { getEmotionEmoji, getEmotionColor } from "../../utils/scoring"
import useAppStore from "../../store/useAppStore"

export default function EmotionPanel() {
  const facialData = useAppStore((s) => s.facialData)
  const emotions   = facialData?.emotions ?? {}
  const dominant   = facialData?.dominant_emotion ?? "neutral"
  const faceFound  = facialData?.face_detected ?? false

  const sorted = Object.entries(emotions).sort(([, a], [, b]) => b - a).slice(0, 5)

  return (
    <div className="glass rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-gray-500 text-xs tracking-widest uppercase">Facial Emotion</p>
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          faceFound ? "bg-green-900/30 text-green-500" : "bg-gray-800 text-gray-600"
        }`}>
          {faceFound ? "Detected" : "No face"}
        </span>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <span className="text-3xl">{getEmotionEmoji(dominant)}</span>
        <div>
          <p className="text-white font-medium capitalize">{dominant}</p>
          <p className="text-gray-500 text-xs">
            {Math.round((emotions[dominant] ?? 0) * 100)}% confidence
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {sorted.map(([emotion, prob]) => {
          const color = getEmotionColor(emotion)
          return (
            <div key={emotion}>
              <div className="flex justify-between text-xs mb-0.5">
                <span className="text-gray-400 capitalize">{emotion}</span>
                <span style={{ color }}>{Math.round(prob * 100)}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-1">
                <div className="h-1 rounded-full transition-all duration-500"
                  style={{ width: `${prob * 100}%`, background: color }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}