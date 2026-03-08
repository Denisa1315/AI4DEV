import { TrendingDown, TrendingUp, Minus, Heart, Clock } from "lucide-react"
import { getEliColor, getEliLabel } from "../../utils/scoring"
import ExportPanel from "./ExportPanel"

export default function SessionSummary({ data, onRestart }) {
  const { startEli, endEli, duration, technique, microAction } = data || {}
  const start    = startEli ?? 65
  const end      = endEli   ?? 42
  const improved = end < start
  const delta    = Math.round(Math.abs(start - end))
  const endColor = getEliColor(end)
  const mins     = Math.floor((duration || 0) / 60)
  const secs     = (duration || 0) % 60

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="glass rounded-3xl p-8 max-w-md w-full">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">{improved ? "🌿" : "💙"}</div>
          <h2 className="text-white text-xl font-semibold mb-1">Session Complete</h2>
          <p className="text-gray-500 text-sm">Here's how your session went</p>
        </div>

        {/* ELI change */}
        <div className="flex items-center justify-around mb-6 p-4 bg-gray-800/40 rounded-2xl">
          <div className="text-center">
            <p className="text-gray-500 text-xs mb-1">Started</p>
            <p className="text-2xl font-mono font-bold" style={{ color: getEliColor(start) }}>{Math.round(start)}</p>
            <p className="text-gray-600 text-xs">{getEliLabel(start)}</p>
          </div>
          <div className="flex flex-col items-center">
            {improved ? <TrendingDown size={20} className="text-green-400" />
              : end === start ? <Minus size={20} className="text-gray-500" />
              : <TrendingUp size={20} className="text-orange-400" />}
            <p className="text-xs mt-1" style={{ color: improved ? "#22c55e" : "#f97316" }}>
              {improved ? `−${delta}` : `+${delta}`}
            </p>
          </div>
          <div className="text-center">
            <p className="text-gray-500 text-xs mb-1">Ended</p>
            <p className="text-2xl font-mono font-bold" style={{ color: endColor }}>{Math.round(end)}</p>
            <p className="text-gray-600 text-xs">{getEliLabel(end)}</p>
          </div>
        </div>

        {/* Stats */}
        <div className="space-y-3 mb-6">
          <div className="flex items-center gap-3 text-sm">
            <Clock size={15} className="text-gray-600" />
            <span className="text-gray-400">Session length: <span className="text-white">{mins}m {secs}s</span></span>
          </div>
          {technique && (
            <div className="flex items-center gap-3 text-sm">
              <Heart size={15} className="text-gray-600" />
              <span className="text-gray-400">Technique used: <span className="text-white">{technique}</span></span>
            </div>
          )}
        </div>

        {/* Micro action */}
        {microAction && (
          <div className="bg-blue-900/20 border border-blue-800/30 rounded-xl p-4 mb-6">
            <p className="text-blue-400 text-xs uppercase tracking-widest mb-1">Your action for today</p>
            <p className="text-gray-200 text-sm leading-relaxed">{microAction}</p>
          </div>
        )}

        {/* ── EXPORT PANEL ── */}
        <div className="mb-6">
          <ExportPanel sessionData={data} />
        </div>

        <button onClick={onRestart}
          className="w-full py-3 rounded-xl text-sm font-medium transition-colors
            bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white border border-gray-700/50">
          Start New Session
        </button>
      </div>
    </div>
  )
}