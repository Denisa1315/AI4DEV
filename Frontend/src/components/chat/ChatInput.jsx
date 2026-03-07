import { useState, forwardRef } from "react"
import { Send }                  from "lucide-react"
import { useTypingMetrics }      from "../../hooks/useTypingMetrics"
import { getEliColor }           from "../../utils/scoring"
import useAppStore               from "../../store/useAppStore"

const ChatInput = forwardRef(function ChatInput({ onSend, disabled, placeholder }, ref) {
  const [input, setInput] = useState("")
  const eliData    = useAppStore((s) => s.eliData)
  const setTyping  = useAppStore((s) => s.setTypingScore)
  const eliColor   = getEliColor(eliData?.eli ?? 50)

  const { handleKeyDown, handleSend } = useTypingMetrics((score) => setTyping(score))

  const submit = () => {
    const text = input.trim()
    if (!text || disabled) return
    const typingScore = handleSend(text.length)
    setInput("")
    onSend(text, typingScore)
  }

  return (
    <div className="flex gap-2 items-end">
      <div className="flex-1 relative">
        <textarea
          ref={ref}
          rows={1}
          value={input}
          onChange={(e) => {
            setInput(e.target.value)
            e.target.style.height = "auto"
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px"
          }}
          onKeyDown={(e) => {
            handleKeyDown(e)
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder={placeholder || "How are you feeling right now..."}
          disabled={disabled}
          style={{ resize: "none", minHeight: "42px", maxHeight: "120px" }}
          className="w-full bg-gray-800/60 rounded-xl px-4 py-2.5 text-sm text-white
            placeholder-gray-600 outline-none focus:ring-1 focus:ring-gray-700
            border border-gray-700/40 focus:border-gray-600/60 transition-colors
            disabled:opacity-40 overflow-hidden leading-relaxed"
        />
        {input.length > 0 && (
          <div
            className="absolute right-3 bottom-3 w-1.5 h-1.5 rounded-full transition-colors duration-500"
            style={{ background: eliColor, opacity: 0.7 }}
          />
        )}
      </div>

      <button
        onClick={submit}
        disabled={!input.trim() || disabled}
        className="shrink-0 p-2.5 rounded-xl transition-all duration-200
          disabled:opacity-30 disabled:cursor-not-allowed hover:scale-105 active:scale-95"
        style={{
          background: eliColor + "25",
          color:      eliColor,
          border:     `1px solid ${eliColor}40`,
        }}
      >
        <Send size={16} />
      </button>
    </div>
  )
})

export default ChatInput