import { getEliColor, getEliLabel, getStatusLabel } from "../../utils/scoring"
import useAppStore from "../../store/useAppStore"

const STATUS_CONFIG = {
  NORMAL: {
    pulse: true,
    extraClass: "",
  },
  MASKING_DETECTED: {
    pulse: false,
    extraClass: "animate-pulse",
    icon: "⚠️",
  },
  CRISIS_RISK: {
    pulse: false,
    extraClass: "",
    icon: "🚨",
  },
  NO_SIGNAL: {
    pulse: false,
    extraClass: "",
    icon: "○",
  },
}

export default function StatusBadge({ showEliLabel = false, size = "sm" }) {
  const eliData = useAppStore((s) => s.eliData)
  const eli     = eliData?.eli    ?? 50
  const status  = eliData?.status ?? "NORMAL"
  const color   = getEliColor(eli)

  const config  = STATUS_CONFIG[status] || STATUS_CONFIG.NORMAL
  const label   = getStatusLabel(status)

  const textSize  = size === "sm" ? "text-xs"  : "text-sm"
  const padSize   = size === "sm" ? "px-2.5 py-1" : "px-3 py-1.5"
  const dotSize   = size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2"

  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full font-medium
      ${textSize} ${padSize} ${config.extraClass} transition-all duration-500`}
      style={{
        background: color + "18",
        color,
        border: `1px solid ${color}35`,
      }}>

      {/* Dot / icon */}
      {config.icon ? (
        <span className="leading-none">{config.icon}</span>
      ) : (
        <span className={`relative flex ${dotSize}`}>
          {config.pulse && (
            <span className={`animate-ping absolute inline-flex h-full w-full
              rounded-full opacity-60`}
              style={{ background: color }} />
          )}
          <span className={`relative inline-flex rounded-full ${dotSize}`}
            style={{ background: color }} />
        </span>
      )}

      {/* Label */}
      <span>{label}</span>

      {/* Optional ELI number next to label */}
      {showEliLabel && (
        <>
          <span className="opacity-30 mx-0.5">·</span>
          <span className="font-mono">{Math.round(eli)}</span>
          <span className="opacity-50 text-xs">{getEliLabel(eli)}</span>
        </>
      )}
    </div>
  )
}