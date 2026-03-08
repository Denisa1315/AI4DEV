import { API_URL } from "../constants"

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function sendChatMessage(message, eliData) {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, eli_payload: eliData }),
  })
}

export async function startSession(userId, currentEli) {
  return request("/api/session/start", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, current_eli: currentEli }),
  })
}

export async function endSession(sessionId, startEli, endEli, durationMinutes) {
  return request("/api/session/end", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId, start_eli: startEli,
      end_eli: endEli, duration_minutes: durationMinutes,
    }),
  })
}

export async function checkHealth() {
  return request("/health")
}

// ── Emotion-aware system prompt builder ──────────────────────────
function buildSystemPrompt(eliData, faceEmotion) {
  const eliScore   = eliData?.eli             ?? 50
  const eliEmotion = eliData?.dominant_emotion ?? "neutral"
  const masking    = eliData?.contradiction_detected ?? false

  const facedom    = faceEmotion?.dominant   ?? "neutral"
  const faceDist   = faceEmotion?.distress   ?? 0
  const faceConf   = faceEmotion?.confidence ?? 0
  const faceEmotions = faceEmotion?.emotions ?? {}

  // Build readable face emotion string
  const topFaceEmotions = Object.entries(faceEmotions)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3)
    .map(([k, v]) => `${k} ${Math.round(v * 100)}%`)
    .join(", ")

  // Decide tone based on BOTH ELI and face
  let tone = "warm and conversational"
  let approach = "Listen openly and validate their experience."

  if (facedom === "sad" || faceDist > 60) {
    tone = "gentle, soft, and deeply empathetic"
    approach = "Acknowledge the sadness visible on their face. Use validating language like 'It makes sense you feel that way'. Don't rush to fix — just be present."
  } else if (facedom === "angry") {
    tone = "calm, measured, and non-reactive"
    approach = "De-escalate gently. Don't challenge. Reflect their frustration back with understanding. Say things like 'That sounds really frustrating'."
  } else if (facedom === "fearful") {
    tone = "steady, reassuring, and grounding"
    approach = "Use grounding language. Remind them they are safe. Offer the 5-4-3-2-1 technique if distress is high."
  } else if (facedom === "happy") {
    tone = "warm, upbeat, and encouraging"
    approach = "Match their positive energy. Celebrate wins. Ask what is going well today."
  } else if (facedom === "surprised") {
    tone = "curious and exploratory"
    approach = "Gently explore what surprised them. Ask open questions."
  } else if (facedom === "disgusted") {
    tone = "non-judgmental and open"
    approach = "Create safety for them to express what is bothering them without judgment."
  }

  if (eliScore > 85) {
    tone = "crisis-level compassion — calm, clear, and immediate"
    approach = "This is a crisis. Stay with them. Validate everything. Suggest iCall helpline 9152987821 gently. Do not leave silence unfilled."
  } else if (masking) {
    approach += " IMPORTANT: Their words say one thing but their face and body say another. Gently name this — say something like 'I notice you said you're okay, but something in how you seem tells me there might be more going on. That's okay — you don't have to be okay right now.'"
  }

  return `You are AffectSync, a compassionate AI mental health companion built for Indian users.

LIVE SENSOR DATA RIGHT NOW:
- ELI (Emotional Load Index): ${eliScore}/100
- ELI Status: ${eliScore < 40 ? "Calm" : eliScore < 65 ? "Mild stress" : eliScore < 85 ? "High stress" : "Crisis"}
- ELI dominant emotion: ${eliEmotion}
- Masking detected: ${masking}

LIVE FACIAL EXPRESSION (from webcam AI):
- Face dominant emotion: ${facedom} (${faceConf}% confidence)
- Top expressions: ${topFaceEmotions || "none detected"}
- Facial distress score: ${faceDist}/100

YOUR TONE RIGHT NOW: ${tone}
YOUR APPROACH: ${approach}

RULES:
- Max 3 sentences unless they ask something specific
- Never say "I'm just an AI"
- Never use clinical jargon — say "feeling heavy" not "depressive episode"
- Understand Indian context: JEE/NEET pressure, family expectations, arranged marriage stress, festival loneliness
- If face shows ${facedom} but they say they are fine — gently name the gap
- ELI > 85: always mention iCall helpline 9152987821
- Respond in the same language mix they use (Hindi-English code-switching is fine)
- Always end with either a question or a grounding suggestion, never a statement that closes the conversation`
}

// ── Main AI response — emotion-aware ─────────────────────────────
export async function getLocalAIResponse(message, eliData, conversationHistory, faceEmotion) {
  try {
    const systemPrompt = buildSystemPrompt(eliData, faceEmotion)

    const messages = [
      ...conversationHistory.slice(-8).map(m => ({
        role: m.role, content: m.content,
      })),
      { role: "user", content: message },
    ]

    const res  = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model:      "claude-sonnet-4-20250514",
        max_tokens: 350,
        system:     systemPrompt,
        messages,
      }),
    })
    const data = await res.json()
    const text = data.content?.map(b => b.text || "").join("") || ""

    // Detect therapy mode from response content + face emotion
    let detectedMode = "supportive"
    const facedom = faceEmotion?.dominant ?? "neutral"

    if (eliData?.eli > 85)
      detectedMode = "crisis"
    else if (eliData?.contradiction_detected)
      detectedMode = "validation"
    else if (facedom === "sad" || facedom === "fearful")
      detectedMode = "validation"
    else if (facedom === "angry")
      detectedMode = "grounding"
    else if (text.includes("breathe") || text.includes("ground") || text.includes("notice") || text.includes("5-4-3"))
      detectedMode = "grounding"
    else if (text.includes("evidence") || text.includes("thought") || text.includes("challenge"))
      detectedMode = "cbt"

    return {
      response:               text,
      therapy_mode:           detectedMode,
      contradiction_detected: eliData?.contradiction_detected ?? false,
      face_emotion_used:      facedom,
    }
  } catch {
    return {
      response:     "I'm here with you. Can you tell me more about what you're feeling right now?",
      therapy_mode: "supportive",
      contradiction_detected: false,
    }
  }
}