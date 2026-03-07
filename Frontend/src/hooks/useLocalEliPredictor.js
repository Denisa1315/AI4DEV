import { useEffect, useRef, useCallback } from "react"
import useAppStore from "../store/useAppStore"
import { predictEliLocally } from "../utils/scoring"

export function useLocalEliPredictor() {
  const wsConnected  = useAppStore((s) => s.wsConnected)
  const facialData   = useAppStore((s) => s.facialData)
  const voiceScore   = useAppStore((s) => s.voiceScore)
  const typingScore  = useAppStore((s) => s.typingScore)
  const watchData    = useAppStore((s) => s.watchData)
  const setLocalEli  = useAppStore((s) => s.setLocalEliScore)
  const intervalRef  = useRef(null)

  const predict = useCallback(() => {
    if (wsConnected) return
    const eli = predictEliLocally({
      facialEmotions: facialData?.emotions,
      voiceScore,
      typingScore,
      watchScore: watchData?.physio_score ?? 50,
    })
    setLocalEli(eli)
  }, [wsConnected, facialData, voiceScore, typingScore, watchData, setLocalEli])

  useEffect(() => {
    intervalRef.current = setInterval(predict, 3000)
    return () => clearInterval(intervalRef.current)
  }, [predict])

  return null
}