import { useState, useRef, useEffect, useCallback } from "react"
import * as faceapi from "face-api.js"
import useAppStore from "../store/useAppStore"

const MODEL_URL = "/models"

export const EMOTION_META = {
  neutral:   { label: "Neutral",   emoji: "😐", color: "#9CA3AF", valence: 0    },
  happy:     { label: "Happy",     emoji: "😊", color: "#22c55e", valence: +1   },
  sad:       { label: "Sad",       emoji: "😢", color: "#60A5FA", valence: -0.8 },
  angry:     { label: "Angry",     emoji: "😠", color: "#EF4444", valence: -1   },
  fearful:   { label: "Fearful",   emoji: "😨", color: "#A78BFA", valence: -0.9 },
  disgusted: { label: "Disgusted", emoji: "🤢", color: "#F97316", valence: -0.7 },
  surprised: { label: "Surprised", emoji: "😲", color: "#FBBF24", valence: +0.2 },
}

const SMOOTH_FRAMES = 6

export function useFaceEmotion(videoRef) {
  const [modelsLoaded,   setModelsLoaded]   = useState(false)
  const [loadError,      setLoadError]      = useState(null)
  const [isDetecting,    setIsDetecting]    = useState(false)
  const [faceDetected,   setFaceDetected]   = useState(false)
  const [emotions,       setEmotions]       = useState({})
  const [dominant,       setDominant]       = useState("neutral")
  const [confidence,     setConfidence]     = useState(0)
  const [distressScore,  setDistressScore]  = useState(0)
  const [emotionHistory, setEmotionHistory] = useState([])

  const rafRef    = useRef(null)
  const smoothBuf = useRef([])
  const activeRef = useRef(false)

  const setFacialData = useAppStore((s) => s.setFacialData)
  const setFaceEmotion = useAppStore((s) => s.setFaceEmotion)

  // ── Load models ──────────────────────────────────────────────
  useEffect(() => {
    async function load() {
      try {
        await Promise.all([
          faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
          faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL),
          faceapi.nets.faceLandmark68TinyNet.loadFromUri(MODEL_URL),
        ])
        setModelsLoaded(true)
      } catch (e) {
        setLoadError("Could not load face models. Check public/models/ folder.")
        console.error("face-api load error:", e)
      }
    }
    load()
  }, [])

  // ── Smooth helper ────────────────────────────────────────────
  const smoothEmotions = useCallback((raw) => {
    smoothBuf.current.push(raw)
    if (smoothBuf.current.length > SMOOTH_FRAMES)
      smoothBuf.current.shift()
    const keys    = Object.keys(EMOTION_META)
    const blended = {}
    keys.forEach(k => {
      const sum = smoothBuf.current.reduce((acc, f) => acc + (f[k] || 0), 0)
      blended[k] = sum / smoothBuf.current.length
    })
    return blended
  }, [])

  // ── Distress score ───────────────────────────────────────────
  const computeDistress = useCallback((smoothed) => {
    const neg = (smoothed.sad       || 0) * 0.30
             + (smoothed.fearful   || 0) * 0.30
             + (smoothed.angry     || 0) * 0.25
             + (smoothed.disgusted || 0) * 0.15
    const pos = (smoothed.happy    || 0) * 0.50
    return Math.round(Math.max(0, Math.min(100, (neg - pos * 0.3) * 100)))
  }, [])

  // ── Detection loop ───────────────────────────────────────────
  const detect = useCallback(async () => {
    if (!activeRef.current) return
    const video = videoRef?.current
    if (!video || video.readyState < 2 || video.paused || video.videoWidth === 0) {
      rafRef.current = setTimeout(() => requestAnimationFrame(detect), 200)
      return
    }
    try {
      const result = await faceapi
        .detectSingleFace(
          video,
          new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.45 })
        )
        .withFaceLandmarks(true)
        .withFaceExpressions()

      if (result) {
        const raw      = result.expressions
        const smoothed = smoothEmotions(raw)
        const distress = computeDistress(smoothed)
        const dom      = Object.entries(smoothed).reduce(
          (best, [k, v]) => v > best[1] ? [k, v] : best,
          ["neutral", 0]
        )

        setFaceDetected(true)
        setEmotions(smoothed)
        setDominant(dom[0])
        setConfidence(Math.round(dom[1] * 100))
        setDistressScore(distress)

        setEmotionHistory(prev => {
          const point = { time: Date.now(), dominant: dom[0], distress, ...smoothed }
          return [...prev.slice(-60), point]
        })

        // ── Push into global store ──
        const facialPayload = {
          distress_score:   distress,
          dominant_emotion: dom[0],
          face_detected:    true,
          confidence:       Math.round(dom[1] * 100),
          emotions:         smoothed,
        }
        setFacialData(facialPayload)

        // ── Also push simplified face emotion for chat context ──
        if (setFaceEmotion) {
          setFaceEmotion({
            dominant:  dom[0],
            distress,
            confidence: Math.round(dom[1] * 100),
            emotions:  smoothed,
          })
        }

      } else {
        setFaceDetected(false)
        smoothBuf.current = []
        setFacialData({ ...useAppStore.getState().facialData, face_detected: false })
      }
    } catch {}

    if (activeRef.current)
      rafRef.current = setTimeout(() => requestAnimationFrame(detect), 150)
  }, [videoRef, smoothEmotions, computeDistress, setFacialData, setFaceEmotion])

  const startDetection = useCallback(() => {
    if (!modelsLoaded || activeRef.current) return
    activeRef.current = true
    setIsDetecting(true)
    smoothBuf.current = []
    requestAnimationFrame(detect)
  }, [modelsLoaded, detect])

  const stopDetection = useCallback(() => {
    activeRef.current = false
    setIsDetecting(false)
    if (rafRef.current) clearTimeout(rafRef.current)
  }, [])

  useEffect(() => {
    return () => {
      activeRef.current = false
      if (rafRef.current) clearTimeout(rafRef.current)
    }
  }, [])

  return {
    modelsLoaded, loadError, isDetecting,
    faceDetected, emotions, dominant,
    confidence, distressScore, emotionHistory,
    startDetection, stopDetection,
  }
}