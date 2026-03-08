import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import useAppStore from "../../store/useAppStore"
import { getEliColor } from "../../utils/scoring"

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const val   = payload[0].value
  const color = getEliColor(val)
  return (
    <div className="bg-gray-900 border border-gray-700/50 rounded-lg px-3 py-2 text-xs">
      <span className="font-mono font-bold" style={{ color }}>{val}</span>
      <span className="text-gray-500 ml-1">ELI</span>
    </div>
  )
}

export default function ELIChart() {
  const history = useAppStore((s) => s.eliHistory)
  const eli     = useAppStore((s) => s.eliData?.eli ?? 50)
  const color   = getEliColor(eli)

  if (history.length < 2) return (
    <div className="glass rounded-2xl p-4 flex items-center justify-center" style={{ height: "100px" }}>
      <p className="text-gray-700 text-xs">Collecting data...</p>
    </div>
  )

  return (
    <div className="glass rounded-2xl p-4">
      <p className="text-gray-500 text-xs tracking-widest uppercase mb-3">ELI Timeline</p>
      <ResponsiveContainer width="100%" height={80}>
        <LineChart data={history} margin={{ top: 4, right: 4, bottom: 0, left: -30 }}>
          <XAxis dataKey="time" tick={false} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "#4B5563" }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={40} stroke="#22c55e" strokeDasharray="3 3" strokeOpacity={0.3} />
          <ReferenceLine y={65} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.3} />
          <ReferenceLine y={85} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.3} />
          <Line type="monotone" dataKey="eli" stroke={color} strokeWidth={2} dot={false}
            style={{ filter: `drop-shadow(0 0 4px ${color}60)` }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}