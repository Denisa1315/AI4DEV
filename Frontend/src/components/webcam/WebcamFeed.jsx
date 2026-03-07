import { useRef, useState } from "react"
import Webcam from "react-webcam"
import { getEmotionEmoji, getEmotionColor } from "../../utils/scoring"
import useAppStore from "../../store/useAppStore"

export default function WebcamFeed() {
  const webcamRef    = useRef(null)
  const [on, setOn]  = useState(false)
  const [err, setErr]= useState(null)

  const facialData  = useAppStore((s) => s.facialData)
  const dominant    = facialData?.dominant_emotion ?? "neutral"
  const faceFound   = facialData?.face_detected    ?? false
  const emotionColor = getEmotionColor(dominant)

  return (
    <div className="glass rounded-2xl overflow-hidden relative" style={{ height: "220px" }}>
      {on ? (
        <>
          <Webcam ref={webcamRef} audio={false} mirrored={true}
            videoConstraints={{ width: 480, height: 220, facingMode: "user" }}
            onUserMediaError={() => setErr("Camera denied")}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
          <div className="absolute inset-x-0 bottom-0 h-16"
            style={{ background: "linear-gradient(to top, rgba(10,10,15,0.9), transparent)" }} />

          <div className="absolute bottom-3 left-3 flex items-center gap-2">
            <span className="text-xl">{getEmotionEmoji(dominant)}</span>
            <span className="text-sm font-medium capitalize" style={{ color: emotionColor }}>
              {dominant}
            </span>
            {faceFound && <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />}
          </div>

          <div className="absolute top-3 right-3 text-xs font-mono px-2 py-1 rounded-lg"
            style={{ background: "rgba(0,0,0,0.6)", color: emotionColor, border: `1px solid ${emotionColor}40` }}>
            {Math.round(facialData?.distress_score ?? 50)}
          </div>

          <button onClick={() => setOn(false)}
            className="absolute top-3 left-3 text-xs text-gray-500 hover:text-gray-300 bg-black/50 px-2 py-1 rounded-lg">
            Hide
          </button>
        </>
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center gap-3">
          <div className="text-4xl opacity-20">📷</div>
          <p className="text-gray-600 text-sm text-center px-4">
            {err || "Enable webcam for facial emotion detection"}
          </p>
          {!err && (
            <button onClick={() => setOn(true)}
              className="text-xs text-blue-400 hover:text-blue-300 border border-blue-900/50
                hover:border-blue-700/50 px-4 py-2 rounded-xl transition-colors">
              Enable Camera
            </button>
          )}
        </div>
      )}
    </div>
  )
}