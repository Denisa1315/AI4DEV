import { Brain, MessageSquare, TrendingUp, TrendingDown, Minus } from "lucide-react"
import useAppStore from "../store/useAppStore"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"

const ELI_COLOR = (v) =>
    v < 40 ? "#22c55e" : v < 65 ? "#f59e0b" : v < 85 ? "#f97316" : "#ef4444"

const EMOTION_EMOJI = {
    happy: "😊", sad: "😢", angry: "😠", fear: "😨",
    neutral: "😐", surprise: "😲", disgust: "🤢", contempt: "😒",
}

function MetricCard({ label, value, unit, color, sub }) {
    return (
        <div className="bg-gray-900/60 rounded-xl p-4 border border-gray-800/50">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-2xl font-bold mt-1" style={{ color: color || "#fff" }}>
                {value ?? "—"}<span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>
            </p>
            {sub && <p className="text-xs text-gray-600 mt-1">{sub}</p>}
        </div>
    )
}

export default function DashboardPage({ onGoToChat }) {
    const eliData = useAppStore((s) => s.eliData)
    const watchData = useAppStore((s) => s.watchData)
    const voiceData = useAppStore((s) => s.voiceData)
    const facialData = useAppStore((s) => s.facialData)
    const eliHistory = useAppStore((s) => s.eliHistory)
    const wsConn = useAppStore((s) => s.wsConnected)

    const eli = eliData?.eli ?? 50
    const emotion = eliData?.dominant_emotion ?? "neutral"
    const breakdown = eliData?.breakdown ?? {}

    const TrendIcon = eliData?.eli_trend === "rising" ? TrendingUp
        : eliData?.eli_trend === "falling" ? TrendingDown : Minus

    return (
        <div className="min-h-screen bg-gray-950 text-white p-4" style={{ fontFamily: "'DM Sans', sans-serif" }}>

            {/* ── Header ────────────────────────────────────────── */}
            <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                    <Brain size={18} className="text-blue-400" />
                    <span className="font-semibold">Emora — Dashboard</span>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${wsConn ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />
                        <span className="text-xs text-gray-500">{wsConn ? "Live" : "Disconnected"}</span>
                    </div>
                    <button onClick={onGoToChat}
                        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-xl
              bg-blue-600/20 border border-blue-600/40 text-blue-400 hover:bg-blue-600/30 transition-colors">
                        <MessageSquare size={12} /> Back to Chat
                    </button>
                </div>
            </div>

            {/* ── Main ELI row ──────────────────────────────────── */}
            <div className="grid grid-cols-12 gap-3 mb-3">

                {/* Big ELI */}
                <div className="col-span-3 bg-gray-900/60 rounded-xl p-5 border border-gray-800/50 flex flex-col items-center justify-center">
                    <p className="text-xs text-gray-500 mb-2">Emotional Load Index</p>
                    <div className="relative w-28 h-28 mb-3">
                        <svg viewBox="0 0 100 100" className="rotate-[-90deg]">
                            <circle cx="50" cy="50" r="40" fill="none" stroke="#1f2937" strokeWidth="10" />
                            <circle cx="50" cy="50" r="40" fill="none"
                                stroke={ELI_COLOR(eli)} strokeWidth="10"
                                strokeDasharray={`${eli * 2.513} 251.3`}
                                strokeLinecap="round" className="transition-all duration-1000" />
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span className="text-2xl font-bold" style={{ color: ELI_COLOR(eli) }}>{eli.toFixed(0)}</span>
                            <span className="text-xs text-gray-500">/100</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                        <TrendIcon size={12} className="text-gray-500" />
                        <span className="capitalize">{eliData?.status?.replace("_", " ") ?? "Normal"}</span>
                    </div>
                    <div className="mt-1 text-lg">{EMOTION_EMOJI[emotion] || "😐"}</div>
                    <p className="text-xs text-gray-500 capitalize">{emotion}</p>
                </div>

                {/* ELI History Chart */}
                <div className="col-span-5 bg-gray-900/60 rounded-xl p-4 border border-gray-800/50">
                    <p className="text-xs text-gray-500 mb-3">ELI Trend (last 30 readings)</p>
                    {eliHistory.length > 1 ? (
                        <ResponsiveContainer width="100%" height={160}>
                            <LineChart data={eliHistory}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                                <XAxis dataKey="time" tick={{ fontSize: 9, fill: "#6b7280" }} interval="preserveStartEnd" />
                                <YAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "#6b7280" }} width={28} />
                                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", fontSize: 11 }}
                                    labelStyle={{ color: "#9ca3af" }} itemStyle={{ color: "#60a5fa" }} />
                                <Line type="monotone" dataKey="eli" stroke={ELI_COLOR(eli)}
                                    strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="h-40 flex items-center justify-center text-xs text-gray-600">
                            Waiting for data from WebSocket…
                        </div>
                    )}
                </div>

                {/* Signal Breakdown */}
                <div className="col-span-4 bg-gray-900/60 rounded-xl p-4 border border-gray-800/50">
                    <p className="text-xs text-gray-500 mb-3">Signal Breakdown</p>
                    {Object.keys(breakdown).length > 0 ? (
                        <div className="space-y-3">
                            {Object.entries(breakdown).map(([key, val]) => (
                                <div key={key}>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-gray-400 capitalize">{key}</span>
                                        <span className="text-gray-500">{val.score?.toFixed(0)}/100</span>
                                    </div>
                                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                                        <div className="h-full rounded-full transition-all duration-700"
                                            style={{ width: `${val.score ?? 50}%`, background: ELI_COLOR(val.score ?? 50) }} />
                                    </div>
                                    <p className="text-xs text-gray-700 mt-0.5">weight {(val.weight ?? 0)}% → contributes {val.contribution?.toFixed(1)}</p>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {["Physio (40%)", "Facial (30%)", "Voice (20%)", "Typing (10%)"].map((s) => (
                                <div key={s}>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-gray-500">{s}</span>
                                        <span className="text-gray-600">—</span>
                                    </div>
                                    <div className="h-2 bg-gray-800 rounded-full" />
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Vitals + Voice + Facial row ─────────────────────── */}
            <div className="grid grid-cols-4 gap-3">
                <MetricCard label="Heart Rate" value={watchData?.heart_rate?.toFixed(0)} unit="bpm"
                    color={watchData?.heart_rate > 90 ? "#f97316" : "#22c55e"}
                    sub={watchData?.source ? `Source: ${watchData.source}` : null} />
                <MetricCard label="HRV" value={watchData?.hrv?.toFixed(0)} unit="ms"
                    color={watchData?.hrv < 25 ? "#ef4444" : watchData?.hrv < 40 ? "#f59e0b" : "#22c55e"} />
                <MetricCard label="Sleep" value={watchData?.sleep_hours?.toFixed(1)} unit="hrs"
                    color={watchData?.sleep_hours < 6 ? "#f97316" : "#22c55e"} />
                <MetricCard label="Physio Score" value={watchData?.physio_score?.toFixed(0)} unit="/100"
                    color={ELI_COLOR(watchData?.physio_score ?? 50)} />

                <div className="col-span-2 bg-gray-900/60 rounded-xl p-4 border border-gray-800/50">
                    <p className="text-xs text-gray-500 mb-2">Voice Analysis</p>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                        <div><span className="text-gray-500 text-xs">Voice Stress </span>
                            <span className="font-medium" style={{ color: ELI_COLOR(voiceData?.voice_stress_score ?? 50) }}>
                                {(voiceData?.voice_stress_score ?? 50).toFixed(0)}/100
                            </span>
                        </div>
                        <div><span className="text-gray-500 text-xs">Text Sentiment </span>
                            <span className="font-medium" style={{ color: ELI_COLOR(voiceData?.text_sentiment_score ?? 50) }}>
                                {(voiceData?.text_sentiment_score ?? 50).toFixed(0)}/100
                            </span>
                        </div>
                        <div><span className="text-gray-500 text-xs">Emotion </span>
                            <span className="font-medium capitalize">{voiceData?.dominant_emotion ?? "—"}</span>
                        </div>
                        <div><span className="text-gray-500 text-xs">Contradiction </span>
                            <span className="font-medium" style={{ color: voiceData?.contradiction_detected ? "#f97316" : "#22c55e" }}>
                                {voiceData?.contradiction_detected ? voiceData.contradiction_type : "None"}
                            </span>
                        </div>
                    </div>
                    {voiceData?.transcript && (
                        <p className="text-xs text-gray-600 mt-2 italic truncate">"{voiceData.transcript}"</p>
                    )}
                </div>

                <div className="col-span-2 bg-gray-900/60 rounded-xl p-4 border border-gray-800/50">
                    <p className="text-xs text-gray-500 mb-2">Facial Analysis (Backend)</p>
                    <div className="grid grid-cols-2 gap-2 text-sm mb-2">
                        <div><span className="text-gray-500 text-xs">Distress </span>
                            <span className="font-medium" style={{ color: ELI_COLOR(facialData?.distress_score ?? 50) }}>
                                {(facialData?.distress_score ?? 50).toFixed(0)}/100
                            </span>
                        </div>
                        <div><span className="text-gray-500 text-xs">Confidence </span>
                            <span className="font-medium">{(facialData?.confidence ?? 0).toFixed(0)}%</span>
                        </div>
                        <div><span className="text-gray-500 text-xs">Lighting </span>
                            <span className="font-medium capitalize" style={{ color: facialData?.lighting === "good" ? "#22c55e" : "#f59e0b" }}>
                                {facialData?.lighting ?? "—"}
                            </span>
                        </div>
                        <div><span className="text-gray-500 text-xs">Face </span>
                            <span className="font-medium" style={{ color: facialData?.face_detected ? "#22c55e" : "#9ca3af" }}>
                                {facialData?.face_detected ? "Detected" : "Not found"}
                            </span>
                        </div>
                    </div>
                    {facialData?.emotions && (
                        <div className="flex flex-wrap gap-1">
                            {Object.entries(facialData.emotions)
                                .sort(([, a], [, b]) => b - a)
                                .slice(0, 4)
                                .map(([em, val]) => (
                                    <span key={em} className="text-xs px-1.5 py-0.5 rounded-full bg-gray-800 text-gray-400">
                                        {EMOTION_EMOJI[em]} {(val * 100).toFixed(0)}%
                                    </span>
                                ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
