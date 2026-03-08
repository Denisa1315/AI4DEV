import { useRef, useCallback } from "react"
import useAppStore from "../store/useAppStore"

export function useTypingMetrics(onScoreUpdate) {
  const keystrokeTimes = useRef([])
  const backspaceCount = useRef(0)
  const inputStartTime = useRef(null)
  const setTypingScore = useAppStore((s) => s.setTypingScore)

  const calculate = useCallback((pauseMs = 0, msgLength = 0) => {
    let score = 30

    const times = keystrokeTimes.current
    if (times.length > 3) {
      const gaps     = times.slice(1).map((t, i) => t - times[i])
      const avg      = gaps.reduce((a, b) => a + b, 0) / gaps.length
      const variance = gaps.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / gaps.length

      if (variance > 30000)  score += 10
      if (variance > 80000)  score += 10
      if (variance > 150000) score += 10
      if (avg < 80)          score += 8
      if (avg > 800)         score += 5
    }

    const total  = Math.max(times.length, 1)
    const bsRate = backspaceCount.current / total
    if (bsRate > 0.20) score += 10
    if (bsRate > 0.40) score += 10
    if (bsRate > 0.60) score += 10

    if (pauseMs > 5000)  score += 8
    if (pauseMs > 12000) score += 8
    if (pauseMs > 25000) score += 8

    if (msgLength > 0 && msgLength < 4) score += 10

    const final = Math.max(0, Math.min(100, score))
    setTypingScore(final)
    if (onScoreUpdate) onScoreUpdate(final)
    return final
  }, [onScoreUpdate, setTypingScore])

  const handleKeyDown = useCallback((e) => {
    const now = Date.now()
    if (!inputStartTime.current) inputStartTime.current = now
    keystrokeTimes.current.push(now)
    if (e.key === "Backspace") backspaceCount.current++
    if (keystrokeTimes.current.length % 8 === 0) calculate()
  }, [calculate])

  const handleSend = useCallback((messageLength) => {
    const pause = inputStartTime.current ? Date.now() - inputStartTime.current : 0
    const score = calculate(pause, messageLength)
    keystrokeTimes.current = []
    backspaceCount.current = 0
    inputStartTime.current = null
    return score
  }, [calculate])

  const reset = useCallback(() => {
    keystrokeTimes.current = []
    backspaceCount.current = 0
    inputStartTime.current = null
  }, [])

  return { handleKeyDown, handleSend, reset }
}