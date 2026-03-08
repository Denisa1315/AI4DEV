import { useState, useEffect } from "react"
import SessionStart from "./pages/SessionStart"
import ChatPage from "./pages/ChatPage"
import DashboardPage from "./pages/DashboardPage"
import { useWebSocket } from "./hooks/useWebSocket"

export default function App() {
  const [page, setPage] = useState("start")

  // Titles
  useEffect(() => {
    const titles = {
      start: "Emora — Start",
      chat: "Emora — Live Session 🟢",
      dashboard: "Emora — Dashboard",
    }
    document.title = titles[page] || "Emora"
  }, [page])

  // Keep WebSocket alive once session starts
  useWebSocket()

  if (page === "start") return (
    <SessionStart onStart={() => setPage("chat")} />
  )
  if (page === "dashboard") return (
    <DashboardPage onGoToChat={() => setPage("chat")} />
  )
  return (
    <ChatPage onGoToDashboard={() => setPage("dashboard")} />
  )
}