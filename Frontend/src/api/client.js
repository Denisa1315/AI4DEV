import { API_URL } from "../constants"

// ── REST helpers ──────────────────────────────────────────
async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function checkHealth() {
  return request("/health")
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

// ── Face analysis — send JPEG blob from webcam ────────────
export async function analyzeFaceFrame(blob) {
  const form = new FormData()
  form.append("file", blob, "frame.jpg")
  const res = await fetch(`${API_URL}/api/analyze-face`, {
    method: "POST",
    body: form,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

// ── Streaming chat — calls /api/chat/stream ────────────────
// onToken(str)  called for each streamed token
// onMode(str)   called once at the end with the therapy mode
// onDone()      called when stream is complete
export async function streamChat(message, eliData, { onToken, onMode, onDone, onError }) {
  try {
    const res = await fetch(`${API_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, eli_payload: eliData }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const reader  = res.body.getReader()
    const decoder = new TextDecoder()
    let   buffer  = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() // keep incomplete last line

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        const data = line.slice(6)

        if (data === "[DONE]") {
          onDone?.()
          continue
        }

        const metaMatch = data.match(/^\[META\](.+)\[\/META\]$/)
        if (metaMatch) {
          onMode?.(metaMatch[1])
          continue
        }

        // Unescape newlines
        onToken?.(data.replace(/\\n/g, "\n"))
      }
    }
  } catch (e) {
    onError?.(e)
  }
}