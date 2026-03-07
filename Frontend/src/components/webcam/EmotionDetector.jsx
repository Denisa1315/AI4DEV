import { useRef, useState, useEffect, useCallback } from "react"
import Webcam             from "react-webcam"
import { useFaceEmotion } from "../../hooks/useFaceEmotion"

const EMOTION_META = {
  neutral:   { label: "Neutral",   emoji: "😐", color: "#9CA3AF" },
  happy:     { label: "Happy",     emoji: "😊", color: "#22c55e" },
  sad:       { label: "Sad",       emoji: "😢", color: "#60A5FA" },
  angry:     { label: "Angry",     emoji: "😠", color: "#EF4444" },
  fearful:   { label: "Fearful",   emoji: "😨", color: "#A78BFA" },
  disgusted: { label: "Disgusted", emoji: "🤢", color: "#F97316" },
  surprised: { label: "Surprised", emoji: "😲", color: "#FBBF24" },
}

export default function EmotionDetector({ compact = false }) {
  const webcamRef  = useRef(null)
  const videoRef   = useRef(null)
  const [camOn,    setCamOn]    = useState(false)
  const [camError, setCamError] = useState(null)
  const [showBars, setShowBars] = useState(false)

  // Bridge Webcam component's video element into videoRef for face-api
  const handleWebcamRef = useCallback((node) => {
    webcamRef.current = node
    if (node?.video) videoRef.current = node.video
  }, [])

  const {
    modelsLoaded, loadError, isDetecting,
    faceDetected, emotions, dominant,
    confidence, distressScore,
    startDetection, stopDetection,
  } = useFaceEmotion(videoRef)

  // Start detection once camera is on and models loaded
  useEffect(() => {
    if (camOn && modelsLoaded) {
      const t = setTimeout(startDetection, 800)
      return () => clearTimeout(t)
    } else {
      stopDetection()
    }
  }, [camOn, modelsLoaded, startDetection, stopDetection])

  const meta   = EMOTION_META[dominant] || EMOTION_META.neutral
  const sorted = Object.entries(emotions).sort(([, a], [, b]) => b - a)

  // ── COMPACT MODE — used inside ChatInterface ──────────────────
  if (compact) {
    return (
      <div className="border-b border-gray-800/60 shrink-0">

        {/* ── Row 1: controls + emotion summary ── */}
        <div className="flex items-center gap-2 px-3 py-2">

          {/* Camera toggle */}
          <button
            onClick={() => {
              if (camOn) { setCamOn(false); stopDetection() }
              else       { setCamError(null); setCamOn(true) }
            }}
            disabled={!!loadError}
            className="shrink-0 flex items-center gap-1.5 text-xs px-2.5 py-1.5
              rounded-lg border transition-all hover:scale-105 active:scale-95
              disabled:opacity-40 font-medium"
            style={{
              background:  camOn ? "#22c55e18" : "#1f2937",
              color:       camOn ? "#22c55e"   : "#6B7280",
              borderColor: camOn ? "#22c55e50" : "#374151",
            }}>
            <span>📷</span>
            <span>{camOn ? "Camera On" : "Camera Off"}</span>
            {camOn && isDetecting && (
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            )}
          </button>

          {/* Status messages */}
          {!modelsLoaded && !loadError && (
            <span className="text-xs text-yellow-500/70">Loading AI models...</span>
          )}
          {loadError && (
            <span className="text-xs text-red-400/70">
              ⚠ Models missing — check public/models/
            </span>
          )}

          {/* Live emotion info */}
          {camOn && faceDetected && (
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <span className="text-lg leading-none">{meta.emoji}</span>
              <span className="text-sm font-semibold" style={{ color: meta.color }}>
                {meta.label}
              </span>
              <span className="text-gray-600 text-xs">{confidence}%</span>
              {distressScore > 40 && (
                <span className="text-xs px-1.5 py-0.5 rounded-full shrink-0"
                  style={{
                    color:      meta.color,
                    background: meta.color + "15",
                    border:     `1px solid ${meta.color}30`,
                  }}>
                  Distress {distressScore}
                </span>
              )}
              <span className="text-gray-600 text-xs italic ml-1 shrink-0">
                AI adapting ↗
              </span>
            </div>
          )}

          {camOn && !faceDetected && isDetecting && (
            <span className="text-xs text-gray-500 flex-1">
              👤 Position your face in the camera...
            </span>
          )}

          {!camOn && modelsLoaded && (
            <span className="text-xs text-gray-600 flex-1">
              Enable camera for facial emotion detection
            </span>
          )}

          {/* Show/hide emotion bars toggle */}
          {camOn && faceDetected && (
            <button
              onClick={() => setShowBars(p => !p)}
              className="shrink-0 text-xs text-gray-600 hover:text-gray-400
                px-2 py-1 rounded-lg border border-gray-800 hover:border-gray-600
                transition-colors">
              {showBars ? "▲" : "▼"} Details
            </button>
          )}
        </div>

        {/* ── Row 2: ALWAYS VISIBLE webcam feed when camOn ── */}
        {camOn && (
          <div className="px-3 pb-3">
            <div className="flex gap-3 items-start">

              {/* Webcam feed — always rendered and visible */}
              <div className="relative rounded-xl overflow-hidden shrink-0 bg-gray-900"
                style={{
                  width:  "140px",
                  height: "105px",
                  border: `1px solid ${faceDetected ? meta.color + "50" : "#374151"}`,
                  boxShadow: faceDetected ? `0 0 12px ${meta.color}20` : "none",
                  transition: "border-color 0.5s, box-shadow 0.5s",
                }}>

                <Webcam
                  ref={handleWebcamRef}
                  audio={false}
                  mirrored={true}
                  videoConstraints={{
                    width:      320,
                    height:     240,
                    facingMode: "user",
                  }}
                  onUserMediaError={() => {
                    setCamError("Camera permission denied.")
                    setCamOn(false)
                  }}
                  style={{
                    width:      "100%",
                    height:     "100%",
                    objectFit:  "cover",
                    display:    "block",
                  }}
                />

                {/* Bottom gradient overlay */}
                <div className="absolute inset-x-0 bottom-0 h-10 pointer-events-none"
                  style={{
                    background: "linear-gradient(to top, rgba(10,10,15,0.95), transparent)",
                  }} />

                {/* Face detected — emotion badge on video */}
                {faceDetected ? (
                  <div className="absolute bottom-1.5 left-0 right-0
                    flex items-center justify-center gap-1">
                    <span className="text-base leading-none">{meta.emoji}</span>
                    <span className="text-xs font-semibold leading-none"
                      style={{
                        color:      meta.color,
                        textShadow: `0 0 8px ${meta.color}80`,
                      }}>
                      {meta.label}
                    </span>
                  </div>
                ) : (
                  <div className="absolute bottom-1.5 left-0 right-0
                    flex items-center justify-center">
                    <span className="text-gray-500" style={{ fontSize: "10px" }}>
                      No face detected
                    </span>
                  </div>
                )}

                {/* Live indicator top-left */}
                <div className="absolute top-1.5 left-1.5 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-green-400" style={{ fontSize: "9px" }}>Live</span>
                </div>

                {/* Confidence top-right */}
                {faceDetected && (
                  <div className="absolute top-1.5 right-1.5">
                    <span className="text-xs font-mono font-bold"
                      style={{
                        color:      meta.color,
                        fontSize:   "9px",
                        textShadow: `0 0 6px ${meta.color}`,
                      }}>
                      {confidence}%
                    </span>
                  </div>
                )}
              </div>

              {/* Right side — emotion bars (when expanded) or mini summary */}
              <div className="flex-1 min-w-0">
                {showBars ? (
                  // Full 7-emotion bars
                  <div className="space-y-1.5">
                    {sorted.map(([emotion, value]) => {
                      const m   = EMOTION_META[emotion] || EMOTION_META.neutral
                      const pct = Math.round(value * 100)
                      const isD = emotion === dominant
                      return (
                        <div key={emotion} className="flex items-center gap-1.5">
                          <span className="text-sm w-5 text-center leading-none shrink-0">
                            {m.emoji}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-center mb-0.5">
                              <span style={{
                                color:    isD ? m.color : "#6B7280",
                                fontSize: "10px",
                                fontWeight: isD ? 600 : 400,
                              }}>
                                {m.label}
                              </span>
                              <span className="font-mono"
                                style={{
                                  color:    isD ? m.color : "#4B5563",
                                  fontSize: "10px",
                                }}>
                                {pct}%
                              </span>
                            </div>
                            <div className="w-full bg-gray-800 rounded-full"
                              style={{ height: "3px" }}>
                              <div className="rounded-full transition-all duration-500"
                                style={{
                                  width:      `${pct}%`,
                                  height:     "3px",
                                  background: isD ? m.color : m.color + "55",
                                  boxShadow:  isD ? `0 0 5px ${m.color}80` : "none",
                                }} />
                            </div>
                          </div>
                          {isD && (
                            <span className="w-1.5 h-1.5 rounded-full shrink-0 animate-pulse"
                              style={{ background: m.color }} />
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  // Collapsed — show top 3 emotions + distress meter
                  <div className="space-y-2">
                    {/* Top 3 emotions */}
                    {sorted.slice(0, 3).map(([emotion, value]) => {
                      const m   = EMOTION_META[emotion] || EMOTION_META.neutral
                      const pct = Math.round(value * 100)
                      const isD = emotion === dominant
                      return (
                        <div key={emotion} className="flex items-center gap-2">
                          <span className="text-sm leading-none shrink-0">{m.emoji}</span>
                          <span style={{
                            color:    isD ? m.color : "#6B7280",
                            fontSize: "11px",
                            fontWeight: isD ? 600 : 400,
                            minWidth: "60px",
                          }}>
                            {m.label}
                          </span>
                          <div className="flex-1 bg-gray-800 rounded-full"
                            style={{ height: "4px" }}>
                            <div className="rounded-full transition-all duration-500"
                              style={{
                                width:      `${pct}%`,
                                height:     "4px",
                                background: isD ? m.color : m.color + "55",
                                boxShadow:  isD ? `0 0 6px ${m.color}70` : "none",
                              }} />
                          </div>
                          <span className="font-mono shrink-0"
                            style={{
                              color:    isD ? m.color : "#4B5563",
                              fontSize: "10px",
                            }}>
                            {pct}%
                          </span>
                        </div>
                      )
                    })}

                    {/* Distress meter */}
                    {faceDetected && (
                      <div className="pt-1 border-t border-gray-800/60">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-gray-600" style={{ fontSize: "10px" }}>
                            Facial Distress
                          </span>
                          <span className="font-mono font-bold"
                            style={{
                              color:    meta.color,
                              fontSize: "10px",
                            }}>
                            {distressScore}/100
                          </span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full"
                          style={{ height: "4px" }}>
                          <div className="rounded-full transition-all duration-700"
                            style={{
                              width:      `${distressScore}%`,
                              height:     "4px",
                              background: `linear-gradient(90deg, #22c55e, ${meta.color})`,
                              boxShadow:  `0 0 6px ${meta.color}50`,
                            }} />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Camera error message */}
        {camError && (
          <div className="px-3 pb-2 text-xs text-red-400 flex items-center gap-2">
            <span>⚠</span>
            <span>{camError}</span>
            <button
              onClick={() => { setCamError(null); setCamOn(true) }}
              className="underline hover:text-red-300 transition-colors">
              Try again
            </button>
          </div>
        )}
      </div>
    )
  }

  return null
}