import { getEliColor, getEliLabel, getStatusLabel } from "../../utils/scoring"
import useAppStore from "../../store/useAppStore"

export default function ELIGauge() {
  const eliData = useAppStore((s) => s.eliData)
  const eli     = eliData?.eli    ?? 50
  const status  = eliData?.status ?? "NORMAL"
  const conf    = eliData?.confidence ?? 70
  const color   = getEliColor(eli)

  const R = 72, cx = 90, cy = 90
  const startDeg = 210, sweep = 240
  const toRad = d => (d * Math.PI) / 180
  const pt    = (deg) => ({ x: cx + R * Math.cos(toRad(deg)), y: cy + R * Math.sin(toRad(deg)) })

  const bgStart = pt(startDeg)
  const bgEnd   = pt(startDeg + sweep)
  const progressDeg = startDeg + (eli / 100) * sweep
  const progressEnd = pt(progressDeg)
  const largeArc = (eli / 100) * sweep > 180 ? 1 : 0

  const isMasking = status === "MASKING_DETECTED"
  const isCrisis  = status === "CRISIS_RISK"

  return (
    <div className="glass rounded-2xl p-5 flex flex-col items-center"
      style={{ borderColor: isCrisis ? "#ef444440" : isMasking ? "#f9730040" : "rgba(255,255,255,0.06)" }}>

      <p className="text-gray-500 text-xs tracking-widest uppercase mb-3">ELI Score</p>

      <svg width="180" height="120" viewBox="0 0 180 120">
        <path
          d={`M ${bgStart.x} ${bgStart.y} A ${R} ${R} 0 1 1 ${bgEnd.x} ${bgEnd.y}`}
          fill="none" stroke="#1f2937" strokeWidth="12" strokeLinecap="round"
        />
        {eli > 0 && (
          <path
            d={`M ${bgStart.x} ${bgStart.y} A ${R} ${R} 0 ${largeArc} 1 ${progressEnd.x} ${progressEnd.y}`}
            fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 8px ${color}80)`, transition: "all 0.8s ease" }}
          />
        )}
        <text x="90" y="82" textAnchor="middle" fontSize="34" fontWeight="700"
          fill={color} fontFamily="'JetBrains Mono', monospace"
          style={{ filter: `drop-shadow(0 0 10px ${color}60)` }}>
          {Math.round(eli)}
        </text>
        <text x="90" y="100" textAnchor="middle" fontSize="11" fill="#6b7280"
          fontFamily="'DM Sans', sans-serif">
          {getEliLabel(eli)}
        </text>
      </svg>

      <div className="mt-1 px-3 py-1 rounded-full text-xs font-medium"
        style={{ background: color + "18", color, border: `1px solid ${color}35` }}>
        {getStatusLabel(status)}
      </div>

      <div className="w-full mt-3">
        <div className="flex justify-between text-xs text-gray-600 mb-1">
          <span>Signal Confidence</span>
          <span style={{ color }}>{conf}%</span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-1">
          <div className="h-1 rounded-full transition-all duration-700"
            style={{ width: `${conf}%`, background: color }} />
        </div>
      </div>

      {isMasking && (
        <div className="mt-3 w-full text-center text-xs text-orange-400 bg-orange-900/20
          border border-orange-800/40 rounded-lg py-2 px-3 animate-fade-in">
          ⚠️ Your words and body language seem different
        </div>
      )}
    </div>
  )
}