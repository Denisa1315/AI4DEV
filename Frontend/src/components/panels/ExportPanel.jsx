import { useState }     from "react"
import { Download, FileText, FileJson, Table, CheckCircle, FilePdf } from "lucide-react"
import {
  exportSessionPDF,
  exportSessionJSON,
  exportConversationCSV,
  exportELITimelineCSV,
  exportSessionReport,
} from "../../utils/exportSession"
import useAppStore from "../../store/useAppStore"

export default function ExportPanel({ sessionData, compact = false }) {
  const [exported, setExported] = useState({})
  const [loading,  setLoading]  = useState({})

  const messages    = useAppStore((s) => s.messages)
  const eliHistory  = useAppStore((s) => s.eliHistory)
  const watchData   = useAppStore((s) => s.watchData)
  const facialData  = useAppStore((s) => s.facialData)
  const voiceData   = useAppStore((s) => s.voiceData)
  const therapyMode = useAppStore((s) => s.therapyMode)
  const sessionId   = useAppStore((s) => s.sessionId)

  const fullData = {
    sessionId,
    therapyMode,
    messages,
    eliHistory,
    watchData,
    facialData,
    voiceData,
    ...sessionData,
  }

  const flash = (key) => {
    setLoading(p  => ({ ...p, [key]: false }))
    setExported(p => ({ ...p, [key]: true  }))
    setTimeout(() => setExported(p => ({ ...p, [key]: false })), 2500)
  }

  const run = async (key, fn) => {
    setLoading(p => ({ ...p, [key]: true }))
    await new Promise(r => setTimeout(r, 80))  // let spinner render
    try { fn() } catch (e) { console.error(e) }
    flash(key)
  }

  const actions = [
    {
      key:     "pdf",
      label:   "PDF Report",
      desc:    "Full styled report — ELI, vitals, conversation, timeline",
      icon:    FileText,
      color:   "#F87171",
      handler: () => run("pdf", () => exportSessionPDF(fullData)),
      primary: true,
    },
    {
      key:     "html",
      label:   "HTML Report",
      desc:    "Open in browser · Print as PDF",
      icon:    FileText,
      color:   "#60A5FA",
      handler: () => run("html", () => exportSessionReport(fullData)),
    },
    {
      key:     "json",
      label:   "Raw Data (JSON)",
      desc:    "Complete session data for analysis",
      icon:    FileJson,
      color:   "#A78BFA",
      handler: () => run("json", () => exportSessionJSON(fullData)),
    },
    {
      key:     "csv",
      label:   "Conversation (CSV)",
      desc:    "All messages with therapy mode tags",
      icon:    Table,
      color:   "#34D399",
      handler: () => run("csv", () => exportConversationCSV(fullData.messages)),
    },
    {
      key:     "eli",
      label:   "ELI Timeline (CSV)",
      desc:    "Every ELI reading with timestamps",
      icon:    Table,
      color:   "#FBBF24",
      handler: () => run("eli", () => exportELITimelineCSV(fullData.eliHistory)),
    },
  ]

  // ── Compact mode — icon row for dashboard header ─────────────
  if (compact) {
    return (
      <div className="flex items-center gap-1.5">
        {actions.map(({ key, label, icon: Icon, color, handler, primary }) => (
          <button
            key={key}
            onClick={handler}
            title={`Export ${label}`}
            disabled={loading[key]}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-xl
              border transition-all duration-200 hover:scale-105 active:scale-95
              disabled:opacity-50"
            style={{
              color:       exported[key] ? "#22c55e" : color,
              borderColor: exported[key] ? "#22c55e40" : color + "40",
              background:  exported[key] ? "#22c55e10" : primary ? color + "20" : color + "12",
              fontWeight:  primary ? 600 : 400,
            }}
          >
            {loading[key] ? (
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                style={{ animation: "spin 0.8s linear infinite" }}>
                <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" strokeOpacity="0.2" fill="none"/>
                <path d="M12 2a10 10 0 0 1 10 10" stroke={color} strokeWidth="3" strokeLinecap="round"/>
              </svg>
            ) : exported[key] ? (
              <CheckCircle size={12} />
            ) : (
              <Icon size={12} />
            )}
            {loading[key]  ? "..."
              : exported[key] ? "Saved!"
              : label.split(" ")[0]}
          </button>
        ))}
      </div>
    )
  }

  // ── Full mode — card list for SessionSummary ─────────────────
  return (
    <div className="glass rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Download size={16} className="text-gray-400" />
        <p className="text-gray-300 text-sm font-medium">Export Session Data</p>
      </div>

      <div className="space-y-2">
        {actions.map(({ key, label, desc, icon: Icon, color, handler, primary }) => (
          <button
            key={key}
            onClick={handler}
            disabled={loading[key]}
            className="w-full flex items-center gap-3 p-3 rounded-xl text-left
              border transition-all duration-200 hover:scale-[1.01] active:scale-[0.99]
              disabled:opacity-60 disabled:cursor-wait"
            style={{
              background:  exported[key] ? "#22c55e12" : primary ? color + "18" : color + "0d",
              borderColor: exported[key] ? "#22c55e40" : primary ? color + "50" : color + "30",
              boxShadow:   primary && !exported[key] ? `0 0 12px ${color}20` : "none",
            }}
          >
            {/* Icon */}
            <div
              className="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: exported[key] ? "#22c55e20" : color + "20" }}
            >
              {loading[key] ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                  style={{ animation: "spin 0.8s linear infinite" }}>
                  <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="3" strokeOpacity="0.2" fill="none"/>
                  <path d="M12 2a10 10 0 0 1 10 10" stroke={color} strokeWidth="3" strokeLinecap="round"/>
                </svg>
              ) : exported[key] ? (
                <CheckCircle size={18} color="#22c55e" />
              ) : (
                <Icon size={18} color={color} />
              )}
            </div>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium"
                  style={{ color: exported[key] ? "#22c55e" : primary ? "#fff" : "#e2e8f0" }}>
                  {loading[key] ? "Generating..." : exported[key] ? "Downloaded!" : label}
                </p>
                {primary && !exported[key] && !loading[key] && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full font-medium"
                    style={{ background: color + "25", color }}>
                    Recommended
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-600 truncate">{desc}</p>
            </div>

            <Download size={14} style={{ color: exported[key] ? "#22c55e" : color + "80" }} />
          </button>
        ))}
      </div>

      <p className="text-gray-700 text-xs text-center mt-4">
        All data stays on your device. Nothing is uploaded.
      </p>
    </div>
  )
}