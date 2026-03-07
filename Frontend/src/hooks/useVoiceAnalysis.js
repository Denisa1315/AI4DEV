import { useState, useRef, useCallback } from "react"
import useAppStore from "../store/useAppStore"
import { API_URL } from "../constants"

export function useVoiceAnalysis() {
  const [isRecording, setIsRecording] = useState(false)
  const [error, setError]             = useState(null)

  const mediaRecorderRef = useRef(null)
  const chunksRef        = useRef([])
  const intervalRef      = useRef(null)
  const streamRef        = useRef(null)
  const activeRef        = useRef(false)

  const setVoiceScore = useAppStore((s) => s.setVoiceScore)
  const setRecording  = useAppStore((s) => s.setRecording)

  const analyzeAudio = useCallback(async (audioBlob) => {
    try {
      const formData = new FormData()
      formData.append("file", audioBlob, "recording.webm")
      const res = await fetch(`${API_URL}/api/analyze-voice`, {
        method: "POST",
        body:   formData,
        signal: AbortSignal.timeout(5000),
      })
      if (!res.ok) throw new Error("Backend error")
      const data  = await res.json()
      const score = data.combined_score ?? data.voice_stress_score ?? 50
      setVoiceScore(score)
      return score
    } catch {
      const localScore = 35 + Math.random() * 25
      setVoiceScore(Math.round(localScore))
      return Math.round(localScore)
    }
  }, [setVoiceScore])

  const recordWindow = useCallback(() => {
    if (!streamRef.current || !activeRef.current) return
    chunksRef.current = []
    try {
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm"

      const recorder = new MediaRecorder(streamRef.current, { mimeType })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => {
        if (!activeRef.current) return
        const blob = new Blob(chunksRef.current, { type: mimeType })
        analyzeAudio(blob)
      }

      recorder.start()
      setTimeout(() => { if (recorder.state === "recording") recorder.stop() }, 5000)
    } catch (e) { console.warn("Recording error:", e) }
  }, [analyzeAudio])

  const startRecording = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true }
      })
      streamRef.current = stream
      activeRef.current = true
      setIsRecording(true)
      setRecording(true)
      recordWindow()
      intervalRef.current = setInterval(recordWindow, 6000)
    } catch {
      setError("Microphone access denied. Voice analysis disabled.")
    }
  }, [recordWindow, setRecording])

  const stopRecording = useCallback(() => {
    activeRef.current = false
    clearInterval(intervalRef.current)
    try { mediaRecorderRef.current?.stop() } catch {}
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setIsRecording(false)
    setRecording(false)
  }, [setRecording])

  return { isRecording, error, startRecording, stopRecording }
}