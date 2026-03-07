import { useEffect, useCallback }  from "react"
import { LogOut, Brain }           from "lucide-react"
import { useWebSocket }            from "../hooks/useWebSocket"
import { useVoiceAnalysis }        from "../hooks/useVoiceAnalysis"
import { useSessionTimer }         from "../hooks/useSessionTimer"
import { useLocalEliPredictor }    from "../hooks/useLocalEliPredictor"
import ELIGauge                    from "../components/dashboard/ELIGauge"
import VitalsPanel                 from "../components/dashboard/VitalsPanel"
import SignalBreakdown             from "../components/dashboard/SignalBreakdown"
import ELIChart                    from "../components/dashboard/ELIChart"
import ChatInterface               from "../components/chat/ChatInterface"
import ExplainPanel                from "../components/panels/ExplainPanel"
import VoicePanel                  from "../components/panels/VoicePanel"
import ExportPanel                 from "../components/panels/ExportPanel"
import ConnectionStatus            from "../components/common/ConnectionStatus"
import CrisisAlert                 from "../components/common/CrisisAlert"
import useAppStore                 from "../store/useAppStore"
import { endSession }              from "../api/client"

export default function Dashboard({ onEnd }) {
  const { sendTypingScore }                                    = useWebSocket()
  const { isRecording, error, startRecording, stopRecording } = useVoiceAnalysis()
  const { formatted }                                          = useSessionTimer()
  useLocalEliPredictor()

  const eliData          = useAppStore((s) => s.eliData)
  const wsConnected      = useAppStore((s) => s.wsConnected)
  const sessionId        = useAppStore((s) => s.sessionId)
  const sessionStartEli  = useAppStore((s) => s.sessionStartEli)
  const sessionStartTime = useAppStore((s) => s.sessionStartTime)
  const therapyMode      = useAppStore((s) => s.therapyMode)
  const faceEmotion      = useAppStore((s) => s.faceEmotion)
  const storeEnd         = useAppStore((s) => s.endSession)
  const isCrisis         = eliData?.status === "CRISIS_RISK"

  const liveExportData = {
    sessionId,
    startEli:    sessionStartEli,
    endEli:      eliData?.eli ?? 50,
    duration:    sessionStartTime
      ? Math.floor((Date.now() - sessionStartTime) / 1000)
      : 0,
    technique:   "In Progress",
    microAction: "",
  }

  useEffect(() => {
    startRecording()
    return () => stopRecording()
  }, [])

  const handleEnd = useCallback(async () => {
    const endEli   = eliData?.eli ?? 50
    const duration = sessionStartTime
      ? Math.floor((Date.now() - sessionStartTime) / 1000)
      : 0
    const techniqueMap = {
      grounding:  "5-4-3-2-1 Grounding",
      cbt:        "CBT Socratic Questioning",
      validation: "Emotional Validation",
      crisis:     "Crisis De-escalation",
      supportive: "Supportive Conversation",
    }
    const microActions = {
      grounding:  "Take 3 slow breaths before your next stressful situation",
      cbt:        "Write down one unhelpful thought and challenge it gently",
      validation: "Allow yourself to feel without judging the feeling",
      crisis:     "Reach out to someone you trust today",
      supportive: "Do one small thing today that brings you peace",
    }
    try {
      await endSession(sessionId, sessionStartEli, endEli, Math.floor(duration / 60))
    } catch {}
    storeEnd()
    onEnd({
      sessionId,
      startEli:    sessionStartEli,
      endEli,
      duration,
      technique:   techniqueMap[therapyMode]  || "Supportive Conversation",
      microAction: microActions[therapyMode]  || microActions.supportive,
    })
  }, [eliData, sessionId, sessionStartEli, sessionStartTime,
      therapyMode, storeEnd, onEnd])

  return (
    <div className="min-h-screen bg-gray-950 text-white overflow-hidden"
      style={{ fontFamily: "'DM Sans', sans-serif" }}>
      {isCrisis && <CrisisAlert />}

      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="px-5 py-3 border-b border-gray-800/50
        flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Brain size={18} className="text-blue-400" />
          <span className="font-semibold text-sm">AffectSync</span>
          {faceEmotion?.dominant && faceEmotion.dominant !== "neutral" && (
            <span className="text-xs text-gray-500">
              · {faceEmotion.dominant} detected
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-gray-600 text-xs font-mono">{formatted}</span>
          <ExportPanel compact={true} sessionData={liveExportData} />
          <ConnectionStatus connected={wsConnected} />
          <button onClick={handleEnd}
            className="flex items-center gap-1.5 text-xs text-gray-500
              hover:text-gray-300 border border-gray-800 hover:border-gray-600
              px-3 py-1.5 rounded-xl transition-colors">
            <LogOut size={12} /> End
          </button>
        </div>
      </header>

      {/* ── Main Grid ──────────────────────────────────────────── */}
      <div className="p-4 grid grid-cols-12 gap-3"
        style={{ height: "calc(100vh - 53px)" }}>

        {/* LEFT — ELI + vitals + voice */}
        <div className="col-span-3 flex flex-col gap-3 overflow-y-auto">
          <ELIGauge />
          <VitalsPanel />
          <VoicePanel />
          {error && (
            <div className="glass rounded-xl p-3 text-xs text-yellow-600
              border border-yellow-900/30">{error}
            </div>
          )}
        </div>

        {/* ── CENTRE — Chat takes full height, emotion detector inside ── */}
        <div className="col-span-6 min-h-0" style={{ height: "100%" }}>
          <ChatInterface onTypingScore={sendTypingScore} />
        </div>

        {/* RIGHT — ELI chart + signal breakdown + explain */}
        <div className="col-span-3 flex flex-col gap-3 overflow-y-auto">
          <ELIChart />
          <SignalBreakdown />
          <ExplainPanel />
        </div>

      </div>
    </div>
  )
}