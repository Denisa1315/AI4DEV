import { useState, useEffect } from "react"
import useAppStore from "../store/useAppStore"

export function useSessionTimer() {
  const [elapsed, setElapsed]    = useState(0)
  const sessionActive    = useAppStore((s) => s.sessionActive)
  const sessionStartTime = useAppStore((s) => s.sessionStartTime)

  useEffect(() => {
    if (!sessionActive || !sessionStartTime) return
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - sessionStartTime) / 1000))
    }, 1000)
    return () => clearInterval(interval)
  }, [sessionActive, sessionStartTime])

  const minutes   = Math.floor(elapsed / 60)
  const seconds   = elapsed % 60
  const formatted = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`

  return { elapsed, formatted, minutes }
}