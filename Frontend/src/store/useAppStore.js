import { create } from "zustand"
import { MOCK_WS_DATA } from "../constants"

const useAppStore = create((set, get) => ({

  // ── State ────────────────────────────────────────────────────
  eliData:    MOCK_WS_DATA.eli,
  watchData:  MOCK_WS_DATA.watch,
  facialData: MOCK_WS_DATA.facial,
  voiceData:  MOCK_WS_DATA.voice,

  wsConnected:   false,
  backendOnline: false,

  messages:    [],
  isAiTyping:  false,
  therapyMode: "supportive",

  // Live face emotion — used by chat to adapt AI tone
  faceEmotion: {
    dominant:   "neutral",
    distress:   0,
    confidence: 0,
    emotions:   {},
  },

  sessionId:        null,
  sessionStartEli:  null,
  sessionActive:    false,
  sessionStartTime: null,
  openingMessage:   "Hello. How are you feeling today?",

  voiceScore:  50,
  typingScore: 50,
  isRecording: false,

  eliHistory: [],

  // ── Actions ──────────────────────────────────────────────────

  setWsData: (payload) => {
    const history  = get().eliHistory
    const newPoint = {
      time: new Date().toLocaleTimeString("en-IN", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      }),
      eli: payload.eli?.eli ?? 50,
    }
    set({
      eliData:       payload.eli,
      watchData:     payload.watch,
      facialData:    payload.facial,
      voiceData:     payload.voice,
      wsConnected:   true,
      backendOnline: true,
      eliHistory:    [...history.slice(-30), newPoint],
    })
  },

  setWsConnected: (val) => set({ wsConnected: val }),

  setLocalEliScore: (score) => {
    const history  = get().eliHistory
    const newPoint = {
      time: new Date().toLocaleTimeString("en-IN", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
      }),
      eli: score,
    }
    set({
      eliData:    { ...get().eliData, eli: score },
      eliHistory: [...history.slice(-30), newPoint],
    })
  },

  // Live facial data from face-api.js
  setFacialData: (data) => set({ facialData: data }),

  // Simplified face emotion used by chat AI
  setFaceEmotion: (data) => set({ faceEmotion: data }),

  // Chat
  addMessage: (msg) => set((s) => ({
    messages: [...s.messages, { ...msg, timestamp: Date.now() }],
  })),
  setAiTyping:    (val)  => set({ isAiTyping: val }),
  setTherapyMode: (mode) => set({ therapyMode: mode }),

  // Signals
  setVoiceScore:  (score) => set({ voiceScore: score }),
  setTypingScore: (score) => set({ typingScore: score }),
  setRecording:   (val)   => set({ isRecording: val }),

  // Session lifecycle
  startSession: (id, eli, openingMsg) => set({
    sessionId:        id || `session_${Date.now()}`,
    sessionStartEli:  eli,
    sessionActive:    true,
    sessionStartTime: Date.now(),
    messages: openingMsg
      ? [{ role: "assistant", content: openingMsg, timestamp: Date.now() }]
      : [],
  }),

  endSession:    () => set({ sessionActive: false }),
  clearMessages: () => set({ messages: [] }),

}))

export default useAppStore