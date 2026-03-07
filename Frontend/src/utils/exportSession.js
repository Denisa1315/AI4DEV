import { getEliLabel, getEliColor } from "./scoring"
import { jsPDF } from "jspdf"

// ── Helper: trigger a browser file download ──────────────────────
function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement("a")
  a.href     = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ── Helper: hex color → RGB array ────────────────────────────────
function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return [r, g, b]
}

// ── Helper: wrap long text into lines ────────────────────────────
function wrapText(doc, text, maxWidth) {
  return doc.splitTextToSize(text, maxWidth)
}

// ════════════════════════════════════════════════════════════════
// 1.  PDF EXPORT  (main new feature)
// ════════════════════════════════════════════════════════════════
export function exportSessionPDF(sessionData) {
  const {
    sessionId, startEli, endEli, duration,
    technique, microAction, therapyMode,
    messages   = [],
    eliHistory = [],
    watchData  = {},
  } = sessionData

  const doc    = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" })
  const W      = doc.internal.pageSize.getWidth()   // 210
  const H      = doc.internal.pageSize.getHeight()  // 297
  const margin = 16
  const inner  = W - margin * 2
  let   y      = margin

  const date = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })
  const time = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })

  const start    = Math.round(startEli ?? 0)
  const end      = Math.round(endEli   ?? 0)
  const improved = end < start
  const delta    = Math.abs(start - end)
  const mins     = Math.floor((duration ?? 0) / 60)
  const secs     = (duration ?? 0) % 60

  const startColor = getEliColor(start)
  const endColor   = getEliColor(end)

  // ── Palette ──
  const BG        = [10,  10,  15 ]
  const CARD      = [17,  24,  39 ]
  const BORDER    = [55,  65,  81 ]
  const WHITE     = [241, 245, 249]
  const GRAY      = [156, 163, 175]
  const DARKGRAY  = [75,  85,  99 ]
  const BLUE      = [59,  130, 246]
  const GREEN     = [34,  197, 94 ]
  const ORANGE    = [249, 115, 22 ]

  // ── Helpers ─────────────────────────────────────────────────
  const addPage = () => {
    doc.addPage()
    // Fill page background
    doc.setFillColor(...BG)
    doc.rect(0, 0, W, H, "F")
    y = margin
  }

  const checkPageBreak = (needed = 20) => {
    if (y + needed > H - margin) addPage()
  }

  const card = (cardY, cardH, color = CARD, radius = 4) => {
    doc.setFillColor(...color)
    doc.setDrawColor(...BORDER)
    doc.setLineWidth(0.3)
    doc.roundedRect(margin, cardY, inner, cardH, radius, radius, "FD")
  }

  const label = (text, lx, ly, size = 7, color = GRAY) => {
    doc.setFontSize(size)
    doc.setTextColor(...color)
    doc.setFont("helvetica", "normal")
    doc.text(text.toUpperCase(), lx, ly)
  }

  const heading = (text, hx, hy, size = 10, color = WHITE) => {
    doc.setFontSize(size)
    doc.setTextColor(...color)
    doc.setFont("helvetica", "bold")
    doc.text(text, hx, hy)
  }

  const body = (text, bx, by, size = 8.5, color = WHITE) => {
    doc.setFontSize(size)
    doc.setTextColor(...color)
    doc.setFont("helvetica", "normal")
    doc.text(text, bx, by)
  }

  const mono = (text, mx, my, size = 9, color = WHITE) => {
    doc.setFontSize(size)
    doc.setTextColor(...color)
    doc.setFont("courier", "bold")
    doc.text(text, mx, my)
  }

  const pill = (text, px, py, bgColor, textColor = WHITE, w = 30) => {
    doc.setFillColor(...bgColor)
    doc.roundedRect(px, py - 4, w, 6, 1.5, 1.5, "F")
    doc.setFontSize(7)
    doc.setTextColor(...textColor)
    doc.setFont("helvetica", "bold")
    doc.text(text, px + w / 2, py, { align: "center" })
  }

  const hLine = (lx, ly, lw = inner, color = BORDER) => {
    doc.setDrawColor(...color)
    doc.setLineWidth(0.3)
    doc.line(lx, ly, lx + lw, ly)
  }

  const eliBar = (score, bx, by, bw = 60, bh = 4) => {
    const color = hexToRgb(getEliColor(score))
    // Track
    doc.setFillColor(30, 41, 59)
    doc.roundedRect(bx, by, bw, bh, 1, 1, "F")
    // Fill
    doc.setFillColor(...color)
    doc.roundedRect(bx, by, (score / 100) * bw, bh, 1, 1, "F")
  }

  // ════════════════════════════════════════════════════════════
  // PAGE 1 — COVER + SUMMARY
  // ════════════════════════════════════════════════════════════
  doc.setFillColor(...BG)
  doc.rect(0, 0, W, H, "F")

  // ── Header strip ──
  doc.setFillColor(17, 24, 57)
  doc.rect(0, 0, W, 38, "F")

  // Brain icon circle
  doc.setFillColor(...BLUE)
  doc.circle(margin + 8, 19, 7, "F")
  doc.setFontSize(12)
  doc.setTextColor(255, 255, 255)
  doc.text("A", margin + 5.5, 22.5)

  // Title
  doc.setFontSize(18)
  doc.setFont("helvetica", "bold")
  doc.setTextColor(...WHITE)
  doc.text("AffectSync", margin + 20, 16)
  doc.setFontSize(9)
  doc.setFont("helvetica", "normal")
  doc.setTextColor(...GRAY)
  doc.text("Session Report", margin + 20, 23)

  // Date + session ID top right
  doc.setFontSize(7.5)
  doc.setTextColor(...GRAY)
  doc.text(`${date}  ·  ${time}`, W - margin, 15, { align: "right" })
  doc.setFontSize(7)
  doc.text(`Session: ${(sessionId || "local").slice(0, 20)}`, W - margin, 22, { align: "right" })

  y = 46

  // ── ELI Summary Card ──────────────────────────────────────
  const eliCardH = 52
  card(y, eliCardH)
  label("Emotional Load Index", margin + 6, y + 8)

  // Start ELI
  const [sr, sg, sb] = hexToRgb(startColor)
  doc.setFontSize(28)
  doc.setFont("courier", "bold")
  doc.setTextColor(sr, sg, sb)
  doc.text(String(start), margin + 22, y + 32, { align: "center" })
  label("START", margin + 8, y + 38)
  label(getEliLabel(start), margin + 8, y + 44, 7, [sr, sg, sb])
  eliBar(start, margin + 6, y + 46, 36)

  // Arrow + delta (center)
  const arrowColor = improved ? GREEN : ORANGE
  doc.setFontSize(20)
  doc.setTextColor(...arrowColor)
  doc.text(improved ? "↓" : "↑", W / 2, y + 28, { align: "center" })
  doc.setFontSize(8)
  doc.setFont("helvetica", "bold")
  doc.text(
    improved ? `−${delta} improved` : `+${delta} increased`,
    W / 2, y + 36, { align: "center" }
  )

  // End ELI
  const [er, eg, eb] = hexToRgb(endColor)
  doc.setFontSize(28)
  doc.setFont("courier", "bold")
  doc.setTextColor(er, eg, eb)
  doc.text(String(end), W - margin - 22, y + 32, { align: "center" })
  label("END", W - margin - 36, y + 38)
  label(getEliLabel(end), W - margin - 36, y + 44, 7, [er, eg, eb])
  eliBar(end, W - margin - 42, y + 46, 36)

  y += eliCardH + 6

  // ── Session Stats Card ────────────────────────────────────
  const statsH = 36
  card(y, statsH)

  const stats = [
    { label: "Duration",   value: `${mins}m ${secs}s`           },
    { label: "Technique",  value: technique || "Supportive"      },
    { label: "HRV",        value: `${watchData.hrv ?? "--"} ms`  },
    { label: "Heart Rate", value: `${watchData.heart_rate ?? "--"} bpm` },
    { label: "Sleep",      value: `${watchData.sleep_hours ?? "--"} hrs` },
    { label: "Messages",   value: String(messages.length)        },
  ]

  const colW = inner / stats.length
  stats.forEach(({ label: l, value: v }, i) => {
    const sx = margin + i * colW + colW / 2
    label(l, sx, y + 12, 6.5, GRAY)
    mono(v,   sx, y + 24, 8.5, WHITE)
    doc.setTextColor(sx, sx, sx)
  })

  y += statsH + 6

  // ── Therapy Mode pill ────────────────────────────────────
  const modeColors = {
    grounding:  [37,  99,  235],
    cbt:        [109, 40,  217],
    validation: [5,   150, 105],
    crisis:     [185, 28,  28 ],
    supportive: [75,  85,  99 ],
  }
  const mColor = modeColors[therapyMode] || modeColors.supportive
  pill(
    `Mode: ${therapyMode || "Supportive"}`,
    margin, y, mColor, WHITE, 55
  )
  y += 12

  // ── Micro action card ────────────────────────────────────
  if (microAction) {
    const actionH = 24
    card(y, actionH, [17, 37, 79])
    label("Your action for today", margin + 6, y + 8, 7, [147, 197, 253])
    const lines = wrapText(doc, microAction, inner - 12)
    doc.setFontSize(8.5)
    doc.setTextColor(...WHITE)
    doc.setFont("helvetica", "normal")
    lines.slice(0, 2).forEach((line, i) => {
      doc.text(line, margin + 6, y + 16 + i * 5)
    })
    y += actionH + 6
  }

  // ── ELI Sparkline ────────────────────────────────────────
  if (eliHistory.length > 1) {
    const sparkH = 30
    card(y, sparkH)
    label("ELI Timeline", margin + 6, y + 8)

    const pts   = eliHistory.slice(-40)
    const bw    = inner - 12
    const bh    = 16
    const bx    = margin + 6
    const by    = y + 10
    const stepX = bw / Math.max(pts.length - 1, 1)

    // Grid lines at 40, 65, 85
    ;[40, 65, 85].forEach(threshold => {
      const ty = by + bh - (threshold / 100) * bh
      doc.setDrawColor(55, 65, 81)
      doc.setLineWidth(0.2)
      doc.line(bx, ty, bx + bw, ty)
    })

    // Sparkline path
    pts.forEach((pt, i) => {
      if (i === 0) return
      const x1 = bx + (i - 1) * stepX
      const y1 = by + bh - (pts[i - 1].eli / 100) * bh
      const x2 = bx + i * stepX
      const y2 = by + bh - (pt.eli / 100) * bh
      const [lr, lg, lb] = hexToRgb(getEliColor(pt.eli))
      doc.setDrawColor(lr, lg, lb)
      doc.setLineWidth(0.8)
      doc.line(x1, y1, x2, y2)
    })

    // Dots at last point
    const last = pts[pts.length - 1]
    const lx2  = bx + (pts.length - 1) * stepX
    const ly2  = by + bh - (last.eli / 100) * bh
    const [lr2, lg2, lb2] = hexToRgb(getEliColor(last.eli))
    doc.setFillColor(lr2, lg2, lb2)
    doc.circle(lx2, ly2, 1.2, "F")

    y += sparkH + 6
  }

  // ── Vitals snapshot ──────────────────────────────────────
  if (watchData && Object.keys(watchData).length > 0) {
    const vitalsH = 22
    card(y, vitalsH)
    label("Vitals Snapshot", margin + 6, y + 8)

    const vitals = [
      { k: "HRV",       v: `${watchData.hrv ?? "--"} ms`,        color: [96, 165, 250] },
      { k: "Heart Rate",v: `${watchData.heart_rate ?? "--"} bpm`, color: [248, 113, 113] },
      { k: "Sleep",     v: `${watchData.sleep_hours ?? "--"} hrs`,color: [167, 139, 250] },
      { k: "Physio",    v: `${watchData.physio_score ?? "--"}/100`,color: [52, 211, 153] },
    ]

    vitals.forEach(({ k, v, color }, i) => {
      const vx = margin + 6 + i * (inner / 4)
      label(k, vx, y + 14, 6, GRAY)
      doc.setFontSize(8)
      doc.setFont("courier", "bold")
      doc.setTextColor(...color)
      doc.text(v, vx, y + 20)
    })

    y += vitalsH + 6
  }

  // ── Footer page 1 ────────────────────────────────────────
  doc.setFontSize(6.5)
  doc.setTextColor(...DARKGRAY)
  doc.text(
    "AffectSync · All data is private and stays on your device",
    W / 2, H - 8, { align: "center" }
  )
  doc.text("1", W - margin, H - 8, { align: "right" })

  // ════════════════════════════════════════════════════════════
  // PAGE 2 — CONVERSATION
  // ════════════════════════════════════════════════════════════
  if (messages.length > 0) {
    addPage()

    // Page heading
    heading("Conversation", margin, y + 6, 13)
    doc.setFontSize(8)
    doc.setTextColor(...GRAY)
    doc.text(`${messages.length} messages`, W - margin, y + 6, { align: "right" })
    y += 14
    hLine(margin, y)
    y += 6

    messages.forEach((msg, idx) => {
      const isUser    = msg.role === "user"
      const fromVoice = msg.fromVoice
      const maxW      = inner * 0.75
      const lines     = wrapText(doc, msg.content || "", maxW - 10)
      const bubbleH   = Math.max(14, lines.length * 5 + 10)

      checkPageBreak(bubbleH + 10)

      const bubbleX = isUser ? W - margin - maxW : margin
      const bgCol   = isUser ? [30, 58, 138] : [31, 41, 55]
      const border  = isUser ? [59, 130, 246] : [55, 65, 81]

      // Bubble background
      doc.setFillColor(...bgCol)
      doc.setDrawColor(...border)
      doc.setLineWidth(0.25)
      doc.roundedRect(bubbleX, y, maxW, bubbleH, 3, 3, "FD")

      // Role label
      doc.setFontSize(6.5)
      doc.setFont("helvetica", "bold")
      doc.setTextColor(...GRAY)
      const roleLabel = isUser
        ? (fromVoice ? "You (voice)" : "You")
        : "AffectSync"
      doc.text(roleLabel, bubbleX + 5, y + 6)

      // Therapy mode tag on AI messages
      if (!isUser && msg.therapyMode) {
        const modeCol = { grounding: BLUE, cbt: [139, 92, 246], validation: GREEN, crisis: [239, 68, 68], supportive: GRAY }[msg.therapyMode] || GRAY
        doc.setFontSize(6)
        doc.setTextColor(...modeCol)
        doc.text(`[${msg.therapyMode}]`, bubbleX + maxW - 5, y + 6, { align: "right" })
      }

      // Message text
      doc.setFontSize(8)
      doc.setFont("helvetica", "normal")
      doc.setTextColor(...WHITE)
      lines.forEach((line, li) => {
        doc.text(line, bubbleX + 5, y + 12 + li * 5)
      })

      // Timestamp
      if (msg.timestamp) {
        doc.setFontSize(5.5)
        doc.setTextColor(...DARKGRAY)
        const ts = new Date(msg.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
        doc.text(ts, isUser ? bubbleX + maxW - 4 : bubbleX + 4, y + bubbleH - 2, { align: isUser ? "right" : "left" })
      }

      y += bubbleH + 4

      // Contradiction notice
      if (!isUser && msg.contradiction) {
        doc.setFontSize(6.5)
        doc.setTextColor(251, 146, 60)
        doc.text("⚠ Verbal-physiological mismatch noted", bubbleX + 5, y)
        y += 5
      }

      // Subtle separator every 5 messages
      if ((idx + 1) % 5 === 0) {
        checkPageBreak(4)
        hLine(margin + inner * 0.2, y, inner * 0.6, [42, 52, 65])
        y += 4
      }
    })

    // Footer page 2
    doc.setFontSize(6.5)
    doc.setTextColor(...DARKGRAY)
    doc.text(
      "AffectSync · All data is private and stays on your device",
      W / 2, H - 8, { align: "center" }
    )
    doc.text("2", W - margin, H - 8, { align: "right" })
  }

  // ════════════════════════════════════════════════════════════
  // PAGE 3 — ELI DATA TABLE  (only if history exists)
  // ════════════════════════════════════════════════════════════
  if (eliHistory.length > 0) {
    addPage()

    heading("ELI Timeline Data", margin, y + 6, 13)
    y += 14
    hLine(margin, y)
    y += 6

    // Table header
    const cols = [
      { label: "#",      w: 12 },
      { label: "Time",   w: 38 },
      { label: "Score",  w: 28 },
      { label: "Status", w: 50 },
      { label: "Bar",    w: inner - 12 - 38 - 28 - 50 },
    ]

    card(y, 10, [31, 41, 55])
    let cx = margin + 4
    cols.forEach(({ label: lbl, w }) => {
      label(lbl, cx, y + 7, 7, [147, 197, 253])
      cx += w
    })
    y += 12

    eliHistory.forEach((pt, i) => {
      checkPageBreak(8)

      const rowBg = i % 2 === 0 ? [17, 24, 39] : [22, 32, 50]
      doc.setFillColor(...rowBg)
      doc.rect(margin, y, inner, 8, "F")

      const [pr, pg, pb] = hexToRgb(getEliColor(pt.eli))
      let rx = margin + 4

      // #
      body(String(i + 1), rx, y + 5.5, 7.5, GRAY)
      rx += cols[0].w

      // Time
      body(pt.time || "--", rx, y + 5.5, 7.5, WHITE)
      rx += cols[1].w

      // Score
      doc.setFontSize(8.5)
      doc.setFont("courier", "bold")
      doc.setTextColor(pr, pg, pb)
      doc.text(String(Math.round(pt.eli)), rx, y + 5.5)
      rx += cols[2].w

      // Status label
      body(getEliLabel(pt.eli), rx, y + 5.5, 7.5, [pr, pg, pb])
      rx += cols[3].w

      // Mini bar
      const barW = cols[4].w - 4
      doc.setFillColor(30, 41, 59)
      doc.roundedRect(rx, y + 2, barW, 4, 1, 1, "F")
      doc.setFillColor(pr, pg, pb)
      doc.roundedRect(rx, y + 2, (pt.eli / 100) * barW, 4, 1, 1, "F")

      y += 8
    })

    // Footer page 3
    doc.setFontSize(6.5)
    doc.setTextColor(...DARKGRAY)
    doc.text(
      "AffectSync · All data is private and stays on your device",
      W / 2, H - 8, { align: "center" }
    )
    doc.text("3", W - margin, H - 8, { align: "right" })
  }

  // ── Save ──────────────────────────────────────────────────
  const filename = `affectsync-report-${new Date().toISOString().slice(0, 10)}.pdf`
  doc.save(filename)
}

// ════════════════════════════════════════════════════════════════
// 2.  JSON EXPORT
// ════════════════════════════════════════════════════════════════
export function exportSessionJSON(sessionData) {
  const {
    sessionId, startEli, endEli, duration,
    technique, microAction, therapyMode,
    messages = [], eliHistory = [], watchData = {}, facialData = {}, voiceData = {},
  } = sessionData

  const payload = {
    meta: {
      exportedAt: new Date().toISOString(),
      sessionId:  sessionId || "unknown",
      appVersion: "AffectSync v1.0",
    },
    summary: {
      startEli:     Math.round(startEli ?? 0),
      endEli:       Math.round(endEli   ?? 0),
      eliChange:    Math.round((startEli ?? 0) - (endEli ?? 0)),
      improved:     (endEli ?? 0) < (startEli ?? 0),
      durationSecs: duration ?? 0,
      durationMins: Math.floor((duration ?? 0) / 60),
      techniqueUsed: technique   || "Supportive Conversation",
      microAction:   microAction || "",
      therapyMode:   therapyMode || "supportive",
    },
    conversation: messages.map((m, i) => ({
      index:         i + 1,
      role:          m.role,
      content:       m.content,
      fromVoice:     m.fromVoice || false,
      therapyMode:   m.therapyMode || null,
      contradiction: m.contradiction || false,
      timestamp:     m.timestamp ? new Date(m.timestamp).toISOString() : null,
    })),
    eliTimeline: eliHistory.map(p => ({
      time:  p.time,
      eli:   Math.round(p.eli),
      label: getEliLabel(p.eli),
    })),
    signalSnapshot: { watch: watchData, facial: facialData, voice: voiceData },
  }

  downloadFile(
    `affectsync-session-${new Date().toISOString().slice(0, 10)}.json`,
    JSON.stringify(payload, null, 2),
    "application/json"
  )
  return payload
}

// ════════════════════════════════════════════════════════════════
// 3.  CONVERSATION CSV
// ════════════════════════════════════════════════════════════════
export function exportConversationCSV(messages = []) {
  const header = ["#", "Role", "From Voice", "Message", "Therapy Mode", "Contradiction", "Time"]
  const rows   = messages.map((m, i) => [
    i + 1,
    m.role,
    m.fromVoice ? "Yes" : "No",
    `"${(m.content || "").replace(/"/g, '""')}"`,
    m.therapyMode || "",
    m.contradiction ? "Yes" : "No",
    m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : "",
  ])
  const csv = [header, ...rows].map(r => r.join(",")).join("\n")
  downloadFile(
    `affectsync-conversation-${new Date().toISOString().slice(0, 10)}.csv`,
    csv,
    "text/csv"
  )
}

// ════════════════════════════════════════════════════════════════
// 4.  ELI TIMELINE CSV
// ════════════════════════════════════════════════════════════════
export function exportELITimelineCSV(eliHistory = []) {
  const header = ["Time", "ELI Score", "Status"]
  const rows   = eliHistory.map(p => [p.time, Math.round(p.eli), getEliLabel(p.eli)])
  const csv    = [header, ...rows].map(r => r.join(",")).join("\n")
  downloadFile(
    `affectsync-eli-timeline-${new Date().toISOString().slice(0, 10)}.csv`,
    csv,
    "text/csv"
  )
}

// ════════════════════════════════════════════════════════════════
// 5.  HTML REPORT  (browser print → PDF fallback)
// ════════════════════════════════════════════════════════════════
export function exportSessionReport(sessionData) {
  const {
    sessionId, startEli, endEli, duration,
    technique, microAction, messages = [], eliHistory = [], watchData = {},
  } = sessionData

  const start    = Math.round(startEli ?? 0)
  const end      = Math.round(endEli   ?? 0)
  const improved = end < start
  const delta    = Math.abs(start - end)
  const mins     = Math.floor((duration ?? 0) / 60)
  const secs     = (duration ?? 0) % 60
  const date     = new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })
  const time     = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
  const startColor = getEliColor(start)
  const endColor   = getEliColor(end)

  const sparkBars = eliHistory.slice(-20).map(p => {
    const h   = Math.round((p.eli / 100) * 40)
    const col = getEliColor(p.eli)
    return `<span style="display:inline-block;width:6px;height:${h}px;background:${col};border-radius:2px;margin:0 1px;vertical-align:bottom;"></span>`
  }).join("")

  const convoHTML = messages.map(m => {
    const isUser = m.role === "user"
    const bg     = isUser ? "#1e3a5f" : "#1a1a2e"
    const align  = isUser ? "right" : "left"
    const label  = isUser ? (m.fromVoice ? "You (voice 🎤)" : "You") : "AffectSync"
    const modeTag = (!isUser && m.therapyMode)
      ? `<span style="font-size:10px;color:#60A5FA;margin-bottom:4px;display:block;">${m.therapyMode}</span>`
      : ""
    return `
      <div style="margin:8px 0;text-align:${align};">
        <div style="display:inline-block;max-width:75%;text-align:left;">
          ${modeTag}
          <div style="background:${bg};border-radius:12px;padding:10px 14px;font-size:13px;color:#e2e8f0;line-height:1.5;">
            <strong style="font-size:10px;color:#94a3b8;display:block;margin-bottom:4px;">${label}</strong>
            ${m.content}
          </div>
        </div>
      </div>`
  }).join("")

  const html = `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AffectSync Report — ${date}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0a0a0f;color:#e2e8f0;padding:32px}
.card{background:rgba(17,24,39,.9);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:24px;margin-bottom:20px}
h1{font-size:24px;font-weight:700;color:#fff}
h2{font-size:14px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.1em;margin-bottom:16px}
.meta{color:#64748b;font-size:12px;margin-top:4px}
.eli-row{display:flex;align-items:center;justify-content:space-around}
.eli-num{font-size:48px;font-weight:700;font-family:monospace}
.eli-label{font-size:12px;color:#94a3b8;margin-top:4px}
.arrow{font-size:28px;text-align:center}
.stat-row{display:flex;gap:12px;flex-wrap:wrap}
.stat{flex:1;min-width:100px;background:rgba(255,255,255,.04);border-radius:10px;padding:12px}
.stat-label{font-size:11px;color:#64748b;margin-bottom:4px}
.stat-value{font-size:18px;font-weight:600;color:#e2e8f0}
.action-box{background:rgba(29,78,216,.15);border:1px solid rgba(59,130,246,.3);border-radius:12px;padding:16px}
.print-btn{background:#1d4ed8;color:#fff;border:none;padding:10px 24px;border-radius:10px;font-size:14px;cursor:pointer;margin-bottom:20px}
@media print{body{background:#fff;color:#000;padding:16px}.card{border:1px solid #e2e8f0;background:#fff}.print-btn{display:none}h1,h2{color:#000}.meta,.eli-label,.stat-label{color:#666}.stat-value{color:#000}}
</style></head>
<body>
<button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
<div class="card">
  <h1>🧠 AffectSync Session Report</h1>
  <p class="meta">${date} at ${time} · Session: ${sessionId || "local"}</p>
</div>
<div class="card">
  <h2>Emotional Load Index</h2>
  <div class="eli-row">
    <div style="text-align:center"><div class="meta">Start</div><div class="eli-num" style="color:${startColor}">${start}</div><div class="eli-label">${getEliLabel(start)}</div></div>
    <div><div class="arrow" style="color:${improved?"#22c55e":"#f97316"}">${improved?"↓":"↑"}</div><div style="font-size:13px;color:${improved?"#22c55e":"#f97316"};text-align:center">${improved?`−${delta} improved`:`+${delta} increased`}</div></div>
    <div style="text-align:center"><div class="meta">End</div><div class="eli-num" style="color:${endColor}">${end}</div><div class="eli-label">${getEliLabel(end)}</div></div>
  </div>
  ${sparkBars?`<div style="margin-top:20px"><div class="meta" style="margin-bottom:6px">ELI Timeline</div><div style="height:44px;display:flex;align-items:flex-end">${sparkBars}</div></div>`:""}
</div>
<div class="card">
  <h2>Session Details</h2>
  <div class="stat-row">
    <div class="stat"><div class="stat-label">Duration</div><div class="stat-value">${mins}m ${secs}s</div></div>
    <div class="stat"><div class="stat-label">Technique</div><div class="stat-value" style="font-size:13px">${technique||"Supportive"}</div></div>
    <div class="stat"><div class="stat-label">HRV</div><div class="stat-value">${watchData.hrv??"--"} ms</div></div>
    <div class="stat"><div class="stat-label">Heart Rate</div><div class="stat-value">${watchData.heart_rate??"--"} bpm</div></div>
    <div class="stat"><div class="stat-label">Sleep</div><div class="stat-value">${watchData.sleep_hours??"--"} hrs</div></div>
    <div class="stat"><div class="stat-label">Messages</div><div class="stat-value">${messages.length}</div></div>
  </div>
</div>
${microAction?`<div class="card"><h2>Your Action for Today</h2><div class="action-box"><p style="color:#93c5fd;font-size:11px;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px">Next step</p><p style="font-size:14px;line-height:1.6">${microAction}</p></div></div>`:""}
${messages.length>0?`<div class="card"><h2>Conversation (${messages.length} messages)</h2><div style="max-height:600px;overflow-y:auto">${convoHTML}</div></div>`:""}
<p style="text-align:center;color:#374151;font-size:11px;margin-top:20px">Generated by AffectSync · ${date} · All data is private</p>
</body></html>`

  downloadFile(
    `affectsync-report-${new Date().toISOString().slice(0, 10)}.html`,
    html,
    "text/html"
  )
}