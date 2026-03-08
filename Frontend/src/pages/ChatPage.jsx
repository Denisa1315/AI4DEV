import { useState, useRef, useEffect, useCallback } from "react"
import { Mic, MicOff, Send, Brain, Activity, Radio } from "lucide-react"
import useAppStore from "../store/useAppStore"
import { streamChat, analyzeFaceFrame } from "../api/client"
import { THERAPY_MODE_LABELS, THERAPY_MODE_COLORS } from "../constants"

const EMOTION_EMOJI = {
    happy: "😊", sad: "😢", angry: "😠", fear: "😨",
    neutral: "😐", surprise: "😲", disgust: "🤢", contempt: "😒",
}
const ELI_COLOR = (v) =>
    v < 40 ? "#22c55e" : v < 65 ? "#f59e0b" : v < 85 ? "#f97316" : "#ef4444"

const SR_SUPPORTED = !!(window.SpeechRecognition || window.webkitSpeechRecognition)

export default function ChatPage({ onGoToDashboard }) {
    const videoRef = useRef(null)
    const canvasRef = useRef(null)
    const bottomRef = useRef(null)
    const camStream = useRef(null)
    const frameRef = useRef(null)

    // ── Voice recognition state ────────────────────────────
    const srRef = useRef(null)
    const silenceTimer = useRef(null)
    const accumulated = useRef("")   // final chunks since last send
    const voiceModeRef = useRef(true) // avoid stale closure

    const [voiceMode, setVoiceMode] = useState(true)  // always-on by default
    const [isListening, setIsListening] = useState(false)
    const [interimText, setInterimText] = useState("")
    const [voiceActive, setVoiceActive] = useState(false)  // speech detected in this window

    // ── Chat state ─────────────────────────────────────────
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState("")
    const [isTyping, setIsTyping] = useState(false)
    const [therapyMode, setTherapyMode] = useState("supportive")

    // ── Camera / face state ────────────────────────────────
    const [faceData, setFaceData] = useState(null)
    const [camReady, setCamReady] = useState(false)
    const [camError, setCamError] = useState(null)

    const eliData = useAppStore((s) => s.eliData)
    const watchData = useAppStore((s) => s.watchData)
    const voiceData = useAppStore((s) => s.voiceData)

    // ── Send a message ─────────────────────────────────────
    const send = useCallback(async (text) => {
        const trimmed = text?.trim()
        if (!trimmed || isTyping) return
        setInput("")
        setInterimText("")
        accumulated.current = ""

        const userMsg = { role: "user", content: trimmed, id: Date.now() }
        setMessages(prev => [...prev, userMsg])
        setIsTyping(true)

        const aiId = Date.now() + 1
        setMessages(prev => [...prev, { role: "assistant", content: "", id: aiId, streaming: true }])

        // Merge live face data into eli_payload so backend masking detection
        // uses the exact emotion shown on screen, not the lagged WebSocket value
        const faceOverride = faceData ? {
            dominant_emotion: faceData.dominant_emotion,
            facial_distress: faceData.distress_score,
            face_detected: faceData.face_detected,
        } : {}

        await streamChat(trimmed, { ...eliData, ...faceOverride, user_id: "demo_user" }, {

            onToken: (token) => {
                setMessages(prev => prev.map(m =>
                    m.id === aiId ? { ...m, content: m.content + token } : m
                ))
            },
            onMode: (mode) => {
                setTherapyMode(mode)
                setMessages(prev => prev.map(m =>
                    m.id === aiId ? { ...m, therapyMode: mode, streaming: false } : m
                ))
            },
            onDone: () => setIsTyping(false),
            onError: () => {
                setMessages(prev => prev.map(m =>
                    m.id === aiId ? { ...m, content: "I'm here with you. How are you feeling right now?", streaming: false } : m
                ))
                setIsTyping(false)
            },
        })
    }, [isTyping, eliData, faceData])

    // ── Always-on voice recognition ────────────────────────
    const resetSilenceTimer = useCallback((textSoFar) => {
        clearTimeout(silenceTimer.current)
        silenceTimer.current = setTimeout(() => {
            const toSend = textSoFar.trim()
            if (toSend) {
                setInterimText("")
                setVoiceActive(false)
                send(toSend)
                accumulated.current = ""
            }
        }, 2500)
    }, [send])

    // Watchdog refs
    const srRunning = useRef(false)
    const restartDelay = useRef(600)    // ms, exponentially backed off
    const watchdogRef = useRef(null)

    const startSR = useCallback(() => {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition
        if (!SR || !voiceModeRef.current) return

        // Abort previous instance fully — prevents InvalidStateError on restart
        if (srRef.current) {
            try { srRef.current.onend = null; srRef.current.abort() } catch { }
            srRef.current = null
        }

        const sr = new SR()
        srRef.current = sr
        sr.continuous = true
        sr.interimResults = true
        sr.lang = "en-IN"
        sr.maxAlternatives = 1

        sr.onstart = () => {
            srRunning.current = true
            restartDelay.current = 600   // reset backoff on clean start
            setIsListening(true)
        }

        sr.onresult = (e) => {
            let finalChunk = ""
            let interim = ""
            for (let i = e.resultIndex; i < e.results.length; i++) {
                const t = e.results[i][0].transcript
                if (e.results[i].isFinal) finalChunk += t
                else interim += t
            }
            if (finalChunk) {
                accumulated.current = (accumulated.current + " " + finalChunk).trim()
            }
            const displayText = (accumulated.current + " " + interim).trim()
            setInterimText(displayText)
            setVoiceActive(true)
            resetSilenceTimer(accumulated.current + " " + interim)
        }

        sr.onerror = (e) => {
            if (e.error !== "no-speech" && e.error !== "aborted") {
                console.warn("[SR] error:", e.error)
                // Back off harder on real errors (not network issues during no-speech)
                restartDelay.current = Math.min(2400, restartDelay.current * 2)
            }
        }

        sr.onend = () => {
            srRunning.current = false
            setIsListening(false)
            if (voiceModeRef.current) {
                setTimeout(startSR, restartDelay.current)
            }
        }

        try {
            sr.start()
        } catch (err) {
            console.warn("[SR] start() threw:", err.message)
            srRunning.current = false
            restartDelay.current = Math.min(2400, restartDelay.current * 2)
            if (voiceModeRef.current) setTimeout(startSR, restartDelay.current)
        }
    }, [resetSilenceTimer])

    const stopSR = useCallback(() => {
        clearTimeout(silenceTimer.current)
        clearInterval(watchdogRef.current)
        voiceModeRef.current = false
        srRunning.current = false
        if (srRef.current) {
            try { srRef.current.onend = null; srRef.current.abort() } catch { }
            srRef.current = null
        }
        setIsListening(false)
        setInterimText("")
        setVoiceActive(false)
        accumulated.current = ""
    }, [])



    // ── Toggle voice mode ──────────────────────────────────
    const toggleVoiceMode = useCallback(() => {
        setVoiceMode(prev => {
            const next = !prev
            voiceModeRef.current = next
            if (next) startSR()
            else stopSR()
            return next
        })
    }, [startSR, stopSR])

    // ── Start voice on mount + watchdog ────────────────────
    useEffect(() => {
        voiceModeRef.current = true
        if (SR_SUPPORTED) startSR()

        // Watchdog: every 3s, if voice mode is on but SR isn't running → restart
        watchdogRef.current = setInterval(() => {
            if (voiceModeRef.current && !srRunning.current) {
                console.log("[SR] Watchdog restarting SR")
                startSR()
            }
        }, 3000)

        return () => {
            voiceModeRef.current = false
            stopSR()
        }
    }, []) // eslint-disable-line react-hooks/exhaustive-deps


    // ── Webcam ─────────────────────────────────────────────
    useEffect(() => {
        let mounted = true
        navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
            .then((stream) => {
                if (!mounted) { stream.getTracks().forEach(t => t.stop()); return }
                camStream.current = stream
                if (videoRef.current) {
                    videoRef.current.srcObject = stream
                    videoRef.current.onloadedmetadata = () => setCamReady(true)
                }
            })
            .catch(() => setCamError("Camera access denied"))
        return () => {
            mounted = false
            camStream.current?.getTracks().forEach(t => t.stop())
        }
    }, [])

    // ── Frame upload to backend every 2s ──────────────────
    useEffect(() => {
        if (!camReady) return
        const tick = async () => {
            const video = videoRef.current
            const canvas = canvasRef.current
            if (!video || !canvas || video.readyState < 2) return
            const ctx = canvas.getContext("2d")
            canvas.width = 320; canvas.height = 240
            ctx.drawImage(video, 0, 0, 320, 240)
            canvas.toBlob(async (blob) => {
                if (!blob) return
                try { setFaceData(await analyzeFaceFrame(blob)) } catch { }
            }, "image/jpeg", 0.7)
        }
        tick()
        frameRef.current = setInterval(tick, 2000)
        return () => clearInterval(frameRef.current)
    }, [camReady])

    // ── Auto scroll ────────────────────────────────────────
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, isTyping, interimText])

    const handleKey = (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input) }
    }

    const eli = eliData?.eli ?? 50
    const emotion = faceData?.dominant_emotion ?? eliData?.dominant_emotion ?? "neutral"
    const modeColor = THERAPY_MODE_COLORS[therapyMode] || "#9CA3AF"

    return (
        <div className="flex h-screen bg-gray-950 text-white overflow-hidden"
            style={{ fontFamily: "'DM Sans', sans-serif" }}>

            {/* ── LEFT PANEL — wider, bigger face ─────────────── */}
            <div className="w-96 flex-shrink-0 flex flex-col gap-3 p-3 border-r border-gray-800/50 overflow-y-auto">

                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Brain size={16} className="text-blue-400" />
                        <span className="text-sm font-semibold">Emora</span>
                    </div>
                    <button onClick={onGoToDashboard}
                        className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-400 transition-colors">
                        <Activity size={12} /> Dashboard
                    </button>
                </div>

                {/* Webcam — bigger */}
                <div className="relative rounded-xl overflow-hidden bg-gray-900" style={{ height: "280px" }}>
                    {camError
                        ? <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-500">{camError}</div>
                        : <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />}
                    <canvas ref={canvasRef} className="hidden" />

                    {/* Live voice indicator on video */}
                    {voiceMode && (
                        <div className="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 rounded-full text-xs"
                            style={{
                                background: isListening ? "#22c55e20" : "#00000060",
                                border: `1px solid ${isListening ? "#22c55e60" : "#374151"}`,
                                color: isListening ? "#22c55e" : "#6b7280",
                            }}>
                            <Radio size={10} className={isListening && voiceActive ? "animate-pulse" : ""} />
                            {isListening ? (voiceActive ? "Speaking…" : "Listening") : "Mic off"}
                        </div>
                    )}

                    {/* Emotion overlay */}
                    {faceData && (
                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-3">
                            <div className="flex items-center gap-2">
                                <span className="text-2xl">{EMOTION_EMOJI[emotion] || "😐"}</span>
                                <div>
                                    <p className="text-sm font-semibold capitalize">{emotion}</p>
                                    <p className="text-xs" style={{ color: ELI_COLOR(faceData.distress_score) }}>
                                        Distress {faceData.distress_score.toFixed(0)}/100
                                    </p>
                                </div>
                                {faceData.lighting !== "good" && (
                                    <span className="ml-auto text-xs text-yellow-400">
                                        ⚠ {faceData.lighting === "too_dark" ? "Low light" : "Too bright"}
                                    </span>
                                )}
                                {!faceData.face_detected && (
                                    <span className="ml-auto text-xs text-gray-500">No face</span>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Emotion bars */}
                {faceData?.emotions && (
                    <div className="bg-gray-900/60 rounded-xl p-3 border border-gray-800/50">
                        <p className="text-xs text-gray-500 mb-2">Backend Facial Analysis</p>
                        <div className="space-y-1.5">
                            {Object.entries(faceData.emotions)
                                .sort(([, a], [, b]) => b - a)
                                .slice(0, 5)
                                .map(([em, val]) => (
                                    <div key={em} className="flex items-center gap-2">
                                        <span className="text-sm w-4">{EMOTION_EMOJI[em]}</span>
                                        <span className="w-14 text-xs text-gray-500 capitalize">{em}</span>
                                        <div className="flex-1 h-1.5 bg-gray-800 rounded-full">
                                            <div className="h-full bg-blue-500 rounded-full transition-all duration-500"
                                                style={{ width: `${(val * 100).toFixed(0)}%` }} />
                                        </div>
                                        <span className="text-xs text-gray-600 w-8 text-right">{(val * 100).toFixed(0)}%</span>
                                    </div>
                                ))}
                        </div>
                    </div>
                )}

                {/* ELI */}
                <div className="bg-gray-900/60 rounded-xl p-3 border border-gray-800/50">
                    <p className="text-xs text-gray-500 mb-1">Emotional Load Index</p>
                    <div className="flex items-end gap-2 mb-2">
                        <span className="text-3xl font-bold" style={{ color: ELI_COLOR(eli) }}>{eli.toFixed(0)}</span>
                        <span className="text-xs text-gray-500 mb-1">/100</span>
                    </div>
                    <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-1000"
                            style={{ width: `${eli}%`, background: ELI_COLOR(eli) }} />
                    </div>
                    {eliData?.status && eliData.status !== "NORMAL" && (
                        <p className="text-xs mt-1.5" style={{ color: eliData.status === "CRISIS_RISK" ? "#ef4444" : "#f97316" }}>
                            ⚠ {eliData.status === "CRISIS_RISK" ? "Crisis Risk" : "Masking Detected"}
                        </p>
                    )}
                </div>

                {/* Voice + Watch compact */}
                <div className="bg-gray-900/60 rounded-xl p-3 border border-gray-800/50">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                        <div><span className="text-gray-500">Voice stress </span>
                            <span className="font-medium" style={{ color: ELI_COLOR(voiceData?.combined_score ?? 50) }}>
                                {(voiceData?.combined_score ?? 50).toFixed(0)}/100
                            </span>
                        </div>
                        {watchData?.heart_rate && <div><span className="text-gray-500">HR </span>
                            <span className="font-medium">{watchData.heart_rate.toFixed(0)} bpm</span>
                        </div>}
                        {watchData?.hrv && <div><span className="text-gray-500">HRV </span>
                            <span className="font-medium">{watchData.hrv.toFixed(0)} ms</span>
                        </div>}
                        {watchData?.sleep_hours && <div><span className="text-gray-500">Sleep </span>
                            <span className="font-medium">{watchData.sleep_hours.toFixed(1)}h</span>
                        </div>}
                    </div>
                    {voiceData?.contradiction_detected && (
                        <p className="text-xs text-orange-400 mt-1.5">⚠ {voiceData.contradiction_type}</p>
                    )}
                </div>

            </div>

            {/* ── RIGHT PANEL — Chat ────────────────────────────── */}
            <div className="flex-1 flex flex-col min-w-0">

                {/* Chat header */}
                <div className="px-4 py-3 border-b border-gray-800/50 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: ELI_COLOR(eli) }} />
                        <span className="font-medium text-sm">Emora Chat</span>
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded-full"
                        style={{ color: modeColor, background: modeColor + "18", border: `1px solid ${modeColor}30` }}>
                        {THERAPY_MODE_LABELS[therapyMode] || "Supportive"}
                    </span>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
                            <span className="text-5xl">{EMOTION_EMOJI[emotion] || "😐"}</span>
                            <p className="text-gray-400 text-sm">Hello, I'm Emora. How are you feeling today?</p>
                            <p className="text-gray-600 text-xs">
                                {SR_SUPPORTED
                                    ? voiceMode ? "🎙 Voice mode on — just start speaking" : "Type or click the mic to speak"
                                    : "Type your message below"}
                            </p>
                        </div>
                    )}

                    {messages.map(msg => (
                        <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                            <div className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
                ${msg.role === "user"
                                    ? "bg-blue-600 text-white rounded-br-sm"
                                    : "bg-gray-800/80 text-gray-100 rounded-bl-sm border border-gray-700/50"}`}>
                                {msg.content}
                                {msg.streaming && msg.content === "" && (
                                    <span className="inline-flex gap-0.5 items-end h-4">
                                        {[0, 1, 2].map(i => (
                                            <span key={i} className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"
                                                style={{ animationDelay: `${i * 0.15}s` }} />
                                        ))}
                                    </span>
                                )}
                                {msg.streaming && msg.content !== "" && (
                                    <span className="inline-block w-0.5 h-3.5 bg-gray-400 ml-0.5 animate-pulse rounded-sm align-middle" />
                                )}
                                {msg.therapyMode && msg.role === "assistant" && (
                                    <p className="text-xs mt-1.5 opacity-40">{THERAPY_MODE_LABELS[msg.therapyMode]}</p>
                                )}
                            </div>
                        </div>
                    ))}

                    {/* Live voice transcript bubble */}
                    {interimText && (
                        <div className="flex justify-end">
                            <div className="max-w-[75%] px-4 py-3 rounded-2xl text-sm bg-blue-900/40
                text-blue-200/70 italic border border-blue-800/30">
                                {interimText}
                                <span className="inline-block w-1 h-3.5 bg-blue-400 ml-1 animate-pulse rounded-sm align-middle" />
                            </div>
                        </div>
                    )}

                    <div ref={bottomRef} />
                </div>

                {/* Input area */}
                <div className="border-t border-gray-800/50 p-3 shrink-0">

                    {/* Voice status bar */}
                    {voiceMode && isListening && (
                        <div className="flex items-center justify-between mb-2 px-3 py-1.5 rounded-xl text-xs"
                            style={{ background: "#22c55e10", border: "1px solid #22c55e30" }}>
                            <div className="flex items-center gap-2 text-green-400">
                                <div className="flex items-end gap-0.5 h-3">
                                    {[0, 1, 2, 3, 4].map((_, i) => (
                                        <div key={i} className="w-0.5 bg-green-400 rounded-full"
                                            style={{
                                                height: voiceActive ? `${40 + Math.random() * 60}%` : "30%",
                                                transition: "height 0.1s", animationDelay: `${i * 0.1}s`
                                            }} />
                                    ))}
                                </div>
                                {voiceActive ? "Speaking — will send after silence…" : "Listening for your voice…"}
                            </div>
                            <span className="text-gray-600">2.5s silence → auto-send</span>
                        </div>
                    )}

                    <div className="flex items-end gap-2">
                        {/* Voice mode toggle */}
                        {SR_SUPPORTED && (
                            <button onClick={toggleVoiceMode}
                                title={voiceMode ? "Disable voice mode" : "Enable always-on voice mode"}
                                className="shrink-0 p-2.5 rounded-xl transition-all"
                                style={{
                                    background: voiceMode ? (isListening ? "#22c55e20" : "#22c55e10") : "#1f2937",
                                    color: voiceMode ? "#22c55e" : "#9CA3AF",
                                    border: `1px solid ${voiceMode ? "#22c55e50" : "#374151"}`,
                                    boxShadow: voiceMode && isListening ? "0 0 10px #22c55e30" : "none",
                                }}>
                                {voiceMode ? <Mic size={16} /> : <MicOff size={16} />}
                            </button>
                        )}

                        {/* Text input — always available */}
                        <textarea
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKey}
                            placeholder={voiceMode
                                ? interimText ? "Transcribing…" : "Or type here…"
                                : "How are you feeling right now…"}
                            rows={1}
                            className="flex-1 bg-gray-900/60 border border-gray-700/50 rounded-xl px-3 py-2.5 text-sm
                text-white placeholder-gray-600 resize-none outline-none focus:border-gray-600 transition-colors"
                            style={{ minHeight: "44px", maxHeight: "120px" }}
                        />

                        <button onClick={() => send(input)} disabled={!input.trim() || isTyping}
                            className="shrink-0 p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500
                disabled:opacity-30 transition-all"
                            style={{ border: "1px solid #2563eb" }}>
                            <Send size={16} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
