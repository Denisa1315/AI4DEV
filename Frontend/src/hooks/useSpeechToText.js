import { useState, useRef, useCallback, useEffect } from "react"

export function useSpeechToText({ onTranscript, continuous = true }) {
  const [isListening,  setIsListening]  = useState(false)
  const [interimText,  setInterimText]  = useState("")
  const [error,        setError]        = useState(null)
  const [supported,    setSupported]    = useState(false)

  const recognitionRef  = useRef(null)
  const restartRef      = useRef(null)
  const activeRef       = useRef(false)
  const lastTranscript  = useRef("")

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition
    setSupported(!!SpeechRecognition)
  }, [])

  const buildRecognition = useCallback(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return null

    const recognition = new SpeechRecognition()
    recognition.lang              = "en-IN"   // Indian English first
    recognition.continuous        = true
    recognition.interimResults    = true
    recognition.maxAlternatives   = 1

    recognition.onstart = () => {
      setIsListening(true)
      setError(null)
    }

    recognition.onresult = (event) => {
      let interim = ""
      let final   = ""

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          final += transcript + " "
        } else {
          interim += transcript
        }
      }

      setInterimText(interim)

      if (final.trim()) {
        const cleaned = final.trim()
        // Deduplicate — browser sometimes fires the same result twice
        if (cleaned !== lastTranscript.current) {
          lastTranscript.current = cleaned
          onTranscript(cleaned)
        }
      }
    }

    recognition.onerror = (event) => {
      if (event.error === "no-speech") return        // ignore silence
      if (event.error === "aborted")   return        // we stopped it ourselves
      if (event.error === "not-allowed") {
        setError("Microphone permission denied.")
        activeRef.current = false
        setIsListening(false)
        return
      }
      console.warn("SpeechRecognition error:", event.error)
    }

    recognition.onend = () => {
      setInterimText("")
      setIsListening(false)
      // Auto-restart if we're still supposed to be listening
      if (activeRef.current && continuous) {
        restartRef.current = setTimeout(() => {
          try { recognitionRef.current?.start() } catch {}
        }, 300)
      }
    }

    return recognition
  }, [onTranscript, continuous])

  const startListening = useCallback(() => {
    if (!supported) {
      setError("Speech recognition not supported in this browser. Use Chrome.")
      return
    }
    if (activeRef.current) return

    activeRef.current      = true
    lastTranscript.current = ""
    recognitionRef.current = buildRecognition()

    try {
      recognitionRef.current?.start()
    } catch (e) {
      console.warn("Recognition start error:", e)
    }
  }, [supported, buildRecognition])

  const stopListening = useCallback(() => {
    activeRef.current = false
    if (restartRef.current) clearTimeout(restartRef.current)
    try { recognitionRef.current?.stop() } catch {}
    setIsListening(false)
    setInterimText("")
  }, [])

  const toggleListening = useCallback(() => {
    if (isListening) stopListening()
    else             startListening()
  }, [isListening, startListening, stopListening])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      activeRef.current = false
      if (restartRef.current) clearTimeout(restartRef.current)
      try { recognitionRef.current?.stop() } catch {}
    }
  }, [])

  return {
    isListening,
    interimText,
    error,
    supported,
    startListening,
    stopListening,
    toggleListening,
  }
}