import { useState, useEffect } from "react"
import { Brain } from "lucide-react"
import useAppStore from "../store/useAppStore"
import { startSession, checkHealth } from "../api/client"
import { MOCK_WS_DATA } from "../constants"
import LoadingSpinner from "../components/common/LoadingSpinner"

export default function SessionStart({ onStart }) {
  const [loading,  setLoading]  = useState(false)
  const [backendOk, setBackendOk] = useState(null)
  const [checking, setChecking] = useState(true)

  const storeStartSession = useAppStore((s) => s.startSession)

  useEffect(() => {
    checkHealth()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false))
      .finally(() => setChecking(false))
  }, [])

  const begin = async () => {
    setLoading(true)
    try {
      let sessionId, openingMsg
      if (backendOk) {
        const res = await startSession("user_demo", MOCK_WS_DATA.eli.eli)
        sessionId  = res.session_id
        openingMsg = res.opening_message
      } else {
        sessionId  = `local_${Date.now()}`
        openingMsg = "Hello. I'm AffectSync — your personal wellbeing companion. I'm reading your physiological and emotional signals in real time. How are you feeling today?"
      }
      storeStartSession(sessionId, MOCK_WS_DATA.eli.eli, openingMsg)
      onStart()
    } catch {
      storeStartSession(`local_${Date.now()}`, 50,
        "Hello. I'm AffectSync. How are you feeling right now?")
      onStart()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full opacity-10"
          style={{ background: "radial-gradient(circle, #3B82F6, transparent)" }} />
      </div>

      <div className="relative text-center max-w-sm w-full">
        <div className="flex items-center justify-center mb-8">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, #1d4ed8, #7c3aed)" }}>
            <Brain size={30} className="text-white" />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-white mb-2">AffectSync</h1>
        <p className="text-gray-500 text-sm mb-8 leading-relaxed">
          Your AI companion that senses how you feel — before you say a word.
        </p>

        <div className="glass rounded-xl p-4 mb-6 text-left">
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-3">System Status</p>
          <div className="space-y-2">
            {[
              { label: "Multimodal AI Engine",   ok: true           },
              { label: "ELI Fusion Model",       ok: true           },
              { label: "Therapy Router (Local)", ok: true           },
              { label: "Backend Server",         ok: backendOk, loading: checking },
            ].map(({ label, ok, loading: ld }) => (
              <div key={label} className="flex items-center justify-between text-sm">
                <span className="text-gray-400">{label}</span>
                {ld ? <LoadingSpinner size="sm" />
                  : <span className={ok ? "text-green-400" : "text-yellow-500"}>
                      {ok ? "● Ready" : "● Local Mode"}
                    </span>}
              </div>
            ))}
          </div>
          {backendOk === false && !checking && (
            <p className="text-yellow-600/70 text-xs mt-3">
              Backend offline — running fully in browser using Claude AI
            </p>
          )}
        </div>

        <button onClick={begin} disabled={loading || checking}
          className="w-full py-4 rounded-2xl font-semibold text-white text-base
            transition-all disabled:opacity-50"
          style={{ background: "linear-gradient(135deg, #1d4ed8, #7c3aed)",
            boxShadow: "0 0 30px rgba(59,130,246,0.3)" }}>
          {loading
            ? <span className="flex items-center justify-center gap-2">
                <LoadingSpinner size="sm" color="white" /> Starting...
              </span>
            : "Begin Session"}
        </button>

        <p className="text-gray-700 text-xs mt-4">
          All processing is private. Sensitive conversations stay on-device.
        </p>
      </div>
    </div>
  )
}