import { useEffect, useRef, useCallback } from "react"
import useAppStore from "../store/useAppStore"
import { WS_URL } from "../constants"

export function useWebSocket() {
  const ws           = useRef(null)
  const reconnectRef = useRef(null)
  const setWsData    = useAppStore((s) => s.setWsData)
  const setConnected = useAppStore((s) => s.setWsConnected)

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return
    try {
      ws.current = new WebSocket(WS_URL)

      ws.current.onopen = () => {
        setConnected(true)
        if (reconnectRef.current) {
          clearTimeout(reconnectRef.current)
          reconnectRef.current = null
        }
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setWsData(data)
        } catch (e) {
          console.error("WS parse error:", e)
        }
      }

      ws.current.onclose = () => {
        setConnected(false)
        reconnectRef.current = setTimeout(connect, 3000)
      }

      ws.current.onerror = () => ws.current?.close()
    } catch {
      setConnected(false)
      reconnectRef.current = setTimeout(connect, 3000)
    }
  }, [setWsData, setConnected])

  const sendTypingScore = useCallback((score) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ typing_score: score }))
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      ws.current?.close()
    }
  }, [connect])

  return { sendTypingScore }
}