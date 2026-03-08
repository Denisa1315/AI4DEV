import useAppStore from "../../store/useAppStore"

function Vital({ label, value, unit, color, note, isReal }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800/60 last:border-0">
      <div>
        <p className="text-gray-400 text-xs">{label}</p>
        <p className="text-xs mt-0.5" style={{ color: color + "80" }}>{note}</p>
      </div>
      <div className="text-right flex items-end gap-1">
        <span className="text-2xl font-bold font-mono transition-all duration-700" style={{ color }}>
          {typeof value === "number" ? value.toFixed(0) : value}
        </span>
        <span className="text-gray-600 text-xs mb-1">{unit}</span>
        {!isReal && <span className="text-gray-700 text-xs mb-1 ml-1" title="Simulated">~</span>}
      </div>
    </div>
  )
}

export default function VitalsPanel() {
  const watchData = useAppStore((s) => s.watchData)
  const hrv    = watchData?.hrv         ?? 55
  const hr     = watchData?.heart_rate  ?? 72
  const sleep  = watchData?.sleep_hours ?? 7
  const isReal = watchData?.is_real_data ?? false

  return (
    <div className="glass rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-gray-500 text-xs tracking-widest uppercase">Vitals</p>
        {!isReal && <span className="text-gray-700 text-xs">simulated</span>}
      </div>
      <Vital label="HRV"        value={hrv}   unit="ms"  color="#60A5FA"
        note={hrv  < 35  ? "Very Low" : hrv  < 50 ? "Low" : "Healthy"} isReal={isReal} />
      <Vital label="Heart Rate" value={hr}    unit="bpm" color="#F87171"
        note={hr   > 100 ? "Elevated" : hr   > 85 ? "Slightly High" : "Normal"} isReal={isReal} />
      <Vital label="Sleep"      value={sleep} unit="hrs" color="#A78BFA"
        note={sleep < 5  ? "Sleep Debt" : sleep < 6.5 ? "Low" : "Good"} isReal={isReal} />
    </div>
  )
}