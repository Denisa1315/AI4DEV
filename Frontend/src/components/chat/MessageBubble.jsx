import { THERAPY_MODE_LABELS, THERAPY_MODE_COLORS } from "../../constants"

export default function MessageBubble({ message }) {
  const isUser    = message.role === "user"
  const mode      = message.therapyMode
  const modeColor = mode ? THERAPY_MODE_COLORS[mode] : null

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-slide-up`}>
      <div className={`max-w-[80%] flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        {!isUser && mode && (
          <span className="text-xs px-2 py-0.5 rounded-full ml-1"
            style={{ color: modeColor, background: modeColor + "18", border: `1px solid ${modeColor}30` }}>
            {THERAPY_MODE_LABELS[mode] || mode}
          </span>
        )}
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed
          ${isUser
            ? "bg-blue-600/80 text-white rounded-br-sm"
            : "bg-gray-800/80 text-gray-200 rounded-bl-sm border border-gray-700/40"
          }`}>
          {message.content}
        </div>
        {!isUser && message.contradiction && (
          <span className="text-xs text-orange-400/80 ml-1">⚠️ Mismatch noted</span>
        )}
      </div>
    </div>
  )
}