import { useState, useRef, useEffect, useCallback } from "react"
import { Mic, MicOff, Volume2 }                     from "lucide-react"
import useAppStore                                   from "../../store/useAppStore"
import { sendChatMessage, getLocalAIResponse }       from "../../api/client"
import { THERAPY_MODE_LABELS, THERAPY_MODE_COLORS }  from "../../constants"
import { getEliColor }                               from "../../utils/scoring"
import { EMOTION_META }                              from "../../hooks/useFaceEmotion"
import { useSpeechToText }                           from "../../hooks/useSpeechToText"
import EmotionDetector                               from "../webcam/EmotionDetector"
import MessageBubble                                 from "./MessageBubble"
import TypingIndicator                               from "./TypingIndicator"
import ChatInput                                     from "./ChatInput"

export default function ChatInterface({ onTypingScore }) {
  const bottomRef              = useRef(null)
  const [ttsEnabled, setTtsEnabled] = useState(false)

  // ── Store ─────────────────────────────────────────────────────
  const messages      = useAppStore((s) => s.messages)
  const isAiTyping    = useAppStore((s) => s.isAiTyping)
  const eliData       = useAppStore((s) => s.eliData)
  const therapyMode   = useAppStore((s) => s.therapyMode)
  const backendOnline = useAppStore((s) => s.backendOnline)
  const isRecording   = useAppStore((s) => s.isRecording)
  const faceEmotion   = useAppStore((s) => s.faceEmotion)
  const addMessage    = useAppStore((s) => s.addMessage)
  const setAiTyping   = useAppStore((s) => s.setAiTyping)
  const setTherapy    = useAppStore((s) => s.setTherapyMode)

  const faceMeta  = EMOTION_META[faceEmotion?.dominant] || EMOTION_META.neutral
  const modeColor = THERAPY_MODE_COLORS[therapyMode]    || "#9CA3AF"
  const eliColor  = getEliColor(eliData?.eli ?? 50)

  // ── TTS ───────────────────────────────────────────────────────
  const speakResponse = useCallback((text) => {
    if (!window.speechSynthesis || !text || !ttsEnabled) return
    window.speechSynthesis.cancel()
    const u    = new SpeechSynthesisUtterance(text)
    u.lang     = "en-IN"
    u.rate     = 0.95
    u.pitch    = 1.0
    u.volume   = 0.9
    const voices   = window.speechSynthesis.getVoices()
    const preferred = voices.find(v =>
      v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural"))
    ) || voices.find(v => v.lang.startsWith("en"))
    if (preferred) u.voice = preferred
    window.speechSynthesis.speak(u)
  }, [ttsEnabled])

  // ── Core send ─────────────────────────────────────────────────
  const sendToAI = useCallback(async (text, fromVoice = false) => {
    addMessage({ role: "user", content: text, fromVoice })
    setAiTyping(true)
    try {
      const data = backendOnline
        ? await sendChatMessage(text, eliData)
        : await getLocalAIResponse(text, eliData, messages, faceEmotion)

      addMessage({
        role:          "assistant",
        content:       data.response,
        therapyMode:   data.therapy_mode,
        contradiction: data.contradiction_detected,
        faceUsed:      data.face_emotion_used,
      })
      if (data.therapy_mode) setTherapy(data.therapy_mode)
      speakResponse(data.response)
    } catch {
      addMessage({
        role:    "assistant",
        content: "I'm here with you. Can you tell me more about how you're feeling?",
      })
    } finally {
      setAiTyping(false)
    }
  }, [backendOnline, eliData, messages, faceEmotion,
      addMessage, setAiTyping, setTherapy, speakResponse])

  // ── Speech to text ────────────────────────────────────────────
  const handleTranscript = useCallback(async (spokenText) => {
    if (!spokenText.trim() || isAiTyping) return
    await sendToAI(spokenText, true)
  }, [isAiTyping, sendToAI])

  const {
    isListening, interimText, error: sttError,
    supported: sttSupported, toggleListening, stopListening,
  } = useSpeechToText({ onTranscript: handleTranscript, continuous: true })

  // ── Typed message ─────────────────────────────────────────────
  const handleSend = useCallback(async (text, typingScore) => {
    if (onTypingScore) onTypingScore(typingScore)
    await sendToAI(text, false)
  }, [onTypingScore, sendToAI])

  // ── Auto scroll ───────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isAiTyping, interimText])

  // Dynamic placeholder based on face
  const inputPlaceholder = isListening
    ? "Speaking... (click Stop to type)"
    : faceEmotion?.dominant === "sad"     ? "I'm here — take your time..."
    : faceEmotion?.dominant === "angry"   ? "Tell me what's going on..."
    : faceEmotion?.dominant === "fearful" ? "You're safe here, tell me more..."
    : "How are you feeling right now..."

  return (
    <div className="glass rounded-2xl flex flex-col" style={{ height: "100%" }}>

      {/* ── Top header — app name + therapy mode + controls ── */}
      <div className="px-4 py-2.5 border-b border-gray-800/60
        flex items-center justify-between shrink-0">

        {/* Left */}
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full animate-pulse"
            style={{ background: eliColor }} />
          <span className="text-sm text-gray-200 font-semibold">AffectSync</span>
          {!backendOnline && (
            <span className="text-gray-600 text-xs">(Local AI)</span>
          )}
        </div>

        {/* Right — controls */}
        <div className="flex items-center gap-2">
          {/* Recording indicator */}
          {isRecording && !isListening && (
            <div className="flex items-center gap-1 text-xs text-red-400">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
              <span>Mic</span>
            </div>
          )}

          {/* STT listening indicator */}
          {isListening && (
            <div className="flex items-center gap-1.5 text-xs text-green-400
              bg-green-900/20 border border-green-800/40 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              Listening...
            </div>
          )}

          {/* Therapy mode badge */}
          <span className="text-xs px-2 py-0.5 rounded-full"
            style={{
              color:      modeColor,
              background: modeColor + "15",
              border:     `1px solid ${modeColor}30`,
            }}>
            {THERAPY_MODE_LABELS[therapyMode] || "Supportive"}
          </span>

          {/* Mismatch badge */}
          {eliData?.contradiction_detected && (
            <span className="text-xs bg-orange-900/30 text-orange-400
              border border-orange-800/40 px-2 py-0.5 rounded-full">
              ⚠️ Mismatch
            </span>
          )}

          {/* TTS toggle */}
          <button
            onClick={() => {
              setTtsEnabled(p => !p)
              if (ttsEnabled) window.speechSynthesis?.cancel()
            }}
            title={ttsEnabled ? "Mute AI voice" : "Enable AI voice"}
            className="p-1.5 rounded-lg transition-colors"
            style={{
              color:      ttsEnabled ? "#60A5FA" : "#4B5563",
              background: ttsEnabled ? "#60A5FA18" : "transparent",
              border:     `1px solid ${ttsEnabled ? "#60A5FA40" : "#374151"}`,
            }}>
            <Volume2 size={13} />
          </button>
        </div>
      </div>

      {/* ── EMOTION DETECTOR — sits right inside chat, below header ── */}
      <EmotionDetector compact={true} />

      {/* ── Messages area — takes all remaining space ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 py-8">
            <div className="text-5xl">{faceMeta.emoji}</div>
            <div className="text-center px-6">
              <p className="text-gray-300 font-medium mb-1">
                {faceEmotion?.dominant === "sad"
                  ? "I can see you might be going through something"
                  : faceEmotion?.dominant === "angry"
                  ? "Something seems to be bothering you"
                  : faceEmotion?.dominant === "fearful"
                  ? "You seem a little anxious right now"
                  : faceEmotion?.dominant === "happy"
                  ? "You seem to be in a good place today!"
                  : "Hello — I'm here with you"}
              </p>
              <p className="text-gray-600 text-sm">
                {faceEmotion?.dominant === "sad"
                  ? "Whenever you're ready to talk, I'm listening."
                  : faceEmotion?.dominant === "angry"
                  ? "Want to tell me what's going on?"
                  : faceEmotion?.dominant === "fearful"
                  ? "Take your time — you're safe here."
                  : faceEmotion?.dominant === "happy"
                  ? "What's been going well lately?"
                  : "Start by typing or speaking how you feel today."}
              </p>
            </div>
            {sttSupported && (
              <button
                onClick={toggleListening}
                className="flex items-center gap-2 text-xs px-5 py-2.5
                  rounded-xl border transition-all hover:scale-105"
                style={{
                  color:       isListening ? "#22c55e" : "#60A5FA",
                  borderColor: isListening ? "#22c55e50" : "#60A5FA40",
                  background:  isListening ? "#22c55e10" : "#60A5FA10",
                }}>
                {isListening ? <MicOff size={14} /> : <Mic size={14} />}
                {isListening ? "Stop listening" : "Tap to speak"}
              </button>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {/* Interim voice transcript bubble */}
        {interimText && (
          <div className="flex justify-end">
            <div className="max-w-[80%] px-4 py-3 rounded-2xl rounded-br-sm
              text-sm leading-relaxed bg-blue-900/40 text-blue-200/60
              border border-blue-800/30 italic">
              {interimText}
              <span className="inline-block w-1 h-3.5 bg-blue-400 ml-1.5
                animate-pulse rounded-sm align-middle" />
            </div>
          </div>
        )}

        {isAiTyping && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* ── STT error ──────────────────────────────────────────── */}
      {sttError && (
        <div className="mx-3 mb-1 px-3 py-2 rounded-xl text-xs text-yellow-500
          bg-yellow-900/20 border border-yellow-800/30 shrink-0">
          {sttError}
        </div>
      )}

      {/* ── Input area ─────────────────────────────────────────── */}
      <div className="border-t border-gray-800/60 shrink-0">

        {/* Listening banner */}
        {isListening && (
          <div className="flex items-center justify-between px-4 py-2
            bg-green-900/15 border-b border-green-800/20">
            <div className="flex items-center gap-2">
              <div className="flex items-end gap-0.5 h-4">
                {[0,1,2,3,4,5,6].map((_, i) => (
                  <div key={i} className="wave-bar w-0.5 bg-green-400 rounded-full"
                    style={{ height: "100%" }} />
                ))}
              </div>
              <span className="text-green-400 text-xs">
                Speak now — I'm listening
              </span>
            </div>
            <button onClick={stopListening}
              className="text-xs text-gray-500 hover:text-gray-300 underline">
              Stop
            </button>
          </div>
        )}

        {/* Input row */}
        <div className="flex items-end gap-2 p-3">
          {/* Mic button */}
          {sttSupported && (
            <button
              onClick={toggleListening}
              disabled={isAiTyping}
              title={isListening ? "Stop voice" : "Start voice"}
              className="shrink-0 p-2.5 rounded-xl transition-all duration-200
                disabled:opacity-30 hover:scale-105 active:scale-95"
              style={{
                background: isListening ? "#22c55e20" : "#1f2937",
                color:      isListening ? "#22c55e"   : "#9CA3AF",
                border:     `1px solid ${isListening ? "#22c55e50" : "#374151"}`,
                boxShadow:  isListening ? "0 0 12px #22c55e30" : "none",
              }}>
              {isListening ? <MicOff size={16} /> : <Mic size={16} />}
            </button>
          )}

          {/* Text input */}
          <div className="flex-1 min-w-0">
            <ChatInput
              onSend={handleSend}
              disabled={isAiTyping || isListening}
              placeholder={inputPlaceholder}
            />
          </div>
        </div>
      </div>
    </div>
  )
}