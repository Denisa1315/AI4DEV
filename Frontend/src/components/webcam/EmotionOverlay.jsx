import { getEmotionEmoji, getEmotionColor } from "../../utils/scoring"
import useAppStore from "../../store/useAppStore"

export default function EmotionOverlay() {
  const facialData = useAppStore((s) => s.facialData)

  const dominant      = facialData?.dominant_emotion ?? "neutral"
  const faceDetected  = facialData?.face_detected    ?? false
  const distressScore = facialData?.distress_score   ?? 50
  const confidence    = facialData?.confidence       ?? 0
  const emotions      = facialData?.emotions         ?? {}
  const color         = getEmotionColor(dominant)

  // Top 3 emotions for mini bars
  const top3 = Object.entries(emotions)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)

  if (!faceDetected) {
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="bg-black/50 rounded-xl px-3 py-2 text-xs text-gray-500 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-600" />
          No face detected
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Bottom left — dominant emotion badge */}
      <div className="absolute bottom-3 left-3 flex items-center gap-2 animate-fade-in">
        <span className="text-2xl drop-shadow-lg">{getEmotionEmoji(dominant)}</span>
        <div>
          <p className="text-sm font-semibold capitalize leading-tight drop-shadow"
            style={{ color }}>
            {dominant}
          </p>
          <p className="text-xs text-gray-400 leading-tight">
            {Math.round(confidence)}% confidence
          </p>
        </div>
      </div>

      {/* Top right — distress score chip */}
      <div className="absolute top-3 right-3 text-xs font-mono px-2.5 py-1.5 rounded-lg
        flex items-center gap-1.5"
        style={{
          background: "rgba(0,0,0,0.65)",
          color,
          border: `1px solid ${color}50`,
          backdropFilter: "blur(4px)",
        }}>
        <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: color }} />
        {Math.round(distressScore)}
      </div>

      {/* Bottom right — mini emotion bars */}
      {top3.length > 0 && (
        <div className="absolute bottom-3 right-3 flex flex-col gap-1 min-w-[90px]">
          {top3.map(([emotion, prob]) => {
            const c = getEmotionColor(emotion)
            return (
              <div key={emotion} className="flex items-center gap-1.5">
                <span className="text-gray-400 text-xs capitalize w-14 text-right leading-none">
                  {emotion}
                </span>
                <div className="flex-1 bg-black/40 rounded-full h-1">
                  <div className="h-1 rounded-full transition-all duration-500"
                    style={{ width: `${prob * 100}%`, background: c }} />
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Face detected pulse ring (corner indicator) */}
      <div className="absolute top-3 left-3">
        <div className="flex items-center gap-1.5 bg-black/50 rounded-lg px-2 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          <span className="text-green-400 text-xs">Live</span>
        </div>
      </div>
    </>
  )
}