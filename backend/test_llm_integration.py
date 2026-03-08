# test_llm_integration.py
import sys, os, cv2, threading, time
import sounddevice as sd
import numpy as np
import soundfile as sf
import tempfile

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.ml.facial_analysis   import facial_analyzer
from services.ml.voice_analysis     import voice_analyzer
from services.ml.watch_analysis     import watch_analyzer, WatchReading
from services.ml.fusion_engine      import fusion_engine, SignalInput
from services.ml.baseline_model     import baseline_model
from services.agents.therapy_router import route
from faster_whisper import WhisperModel

SAMPLE_RATE    = 16000
WINDOW_SECONDS = 5

# Load Whisper directly here — bypass voice_analysis pipeline entirely
whisper_model = None

state = {
    "facial":     {},
    "voice":      {},
    "watch":      {},
    "eli":        {},
    "transcript": "",
    "response":   {"response": "Starting up — say something!", "agent": "—"},
    "llm_thinking": False,
}

def load_whisper():
    global whisper_model
    print("[Whisper] Loading...")
    whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    print("[Whisper] Ready ✓")

def voice_thread():
    """Record until silence detected, then transcribe."""
    while whisper_model is None:
        time.sleep(0.5)

    print("[Voice] Listening with VAD...")

    CHUNK_SIZE    = 1024
    SILENCE_LIMIT = 2.0    # seconds of silence before stopping
    MIN_SPEECH    = 1.0    # minimum seconds of speech before processing
    SILENCE_RMS   = 0.008  # RMS below this = silence

    while True:
        try:
            audio_chunks  = []
            silence_start = None
            speech_start  = None
            recording     = False

            # Wait for LLM to finish before listening again
            while state.get("llm_thinking", False):
                time.sleep(0.2)
            print("[Mic] Waiting for speech...")

            # Stream audio in chunks
            with sd.InputStream(
                samplerate = SAMPLE_RATE,
                channels   = 1,
                dtype      = 'float32',
                blocksize  = CHUNK_SIZE,
            ) as stream:

                while True:
                    chunk, _ = stream.read(CHUNK_SIZE)
                    chunk    = chunk.flatten()
                    rms      = float(np.sqrt(np.mean(chunk ** 2)))

                    if rms > SILENCE_RMS:
                        # Speech detected
                        if not recording:
                            print("[Mic] Speech detected — recording...")
                            recording    = True
                            speech_start = time.time()
                        audio_chunks.append(chunk)
                        silence_start = None

                    elif recording:
                        # Silence after speech
                        audio_chunks.append(chunk)
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > SILENCE_LIMIT:
                            # Enough silence — stop recording
                            print("[Mic] Silence detected — processing...")
                            break

            # Check we got enough speech
            if not audio_chunks:
                continue

            speech_duration = len(audio_chunks) * CHUNK_SIZE / SAMPLE_RATE
            if speech_duration < MIN_SPEECH:
                print(f"[Mic] Too short ({speech_duration:.1f}s) — skipping")
                continue

            # Transcribe
            audio = np.concatenate(audio_chunks)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, audio, SAMPLE_RATE)
                tmp = f.name

            segments, _ = whisper_model.transcribe(
                tmp,
                language   = "en",
                beam_size  = 5,
                vad_filter = True,
                vad_parameters = dict(min_silence_duration_ms=300)
            )
            os.unlink(tmp)

            transcript = " ".join(s.text.strip() for s in segments).strip()
            print(f"[Mic] Whisper: \"{transcript}\"")

            if transcript:
                state["transcript"] = transcript
                voice_analyzer._process(audio)
                voice_state             = voice_analyzer.to_dict()
                voice_state["transcript"] = transcript
                state["voice"]          = voice_state

        except Exception as e:
            print(f"[Voice] Error: {e}")
            time.sleep(1)

def watch_thread():
    while True:
        watch_analyzer.simulate_and_process("normal")
        state["watch"] = watch_analyzer.to_dict()
        time.sleep(5)

def llm_thread():
    """Run LLM ONLY when transcript changes — never on a timer."""
    last_transcript = ""

    while True:
        time.sleep(1)
        try:
            transcript = state.get("transcript", "")

            # ONLY respond if something new was actually said
            if not transcript:
                continue
            if transcript == last_transcript:
                continue

            eli_data = state.get("eli", {})
            if not eli_data:
                continue

            # Inject current transcript into eli_data for router
            eli_data["transcript"] = transcript

            state["llm_thinking"] = True
            result = route(eli_data)
            state["response"]     = result
            last_transcript       = transcript
            state["llm_thinking"] = False

            print(f"\n{'='*50}")
            print(f"[{result.get('agent','?').upper()}] Heard: \"{transcript}\"")
            print(f"Response: {result.get('response','')}")
            print(f"{'='*50}\n")

        except Exception as e:
            print(f"[LLM] Error: {e}")

def eli_thread():
    """Recalculate ELI every 3 seconds."""
    while True:
        time.sleep(3)
        try:
            f = state.get("facial", {})
            v = state.get("voice",  {})
            w = state.get("watch",  {})

            # Use facial emotion directly — don't let old voice
            # emotion override a clearly happy face
            facial_emotion = f.get("dominant_emotion", "neutral")
            facial_score   = f.get("distress_score", 50)
            facial_conf    = f.get("confidence", 0)

            # If face is clearly happy with high confidence,
            # override voice emotion
            if facial_emotion == "happy" and facial_conf > 70:
                voice_emotion = "happy"
                # Reduce voice stress score when face is clearly happy
                voice_score = min(
                    v.get("combined_score", 50),
                    30.0
                )
            else:
                voice_emotion = v.get("dominant_emotion", "neutral")
                voice_score   = v.get("combined_score", 50)

            result = fusion_engine.calculate(SignalInput(
                physio_score           = w.get("physio_score"),
                facial_score           = facial_score,
                voice_score            = voice_score,
                typing_score           = None,
                contradiction_detected = v.get("contradiction_detected", False),
                contradiction_type     = v.get("contradiction_type", "none"),
                transcript             = state.get("transcript", ""),
                facial_emotion         = facial_emotion,
                voice_emotion          = voice_emotion,
            ))
            state["eli"] = fusion_engine.to_dict(result)

        except Exception as e:
            print(f"[ELI] Error: {e}")

def draw(frame, state):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (340, h), (15, 15, 25), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)

    def txt(text, x, y, color=(255,255,255), scale=0.5, bold=False):
        cv2.putText(frame, str(text), (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color,
                    2 if bold else 1, cv2.LINE_AA)

    def bar(x, y, bw, bh, val, col):
        cv2.rectangle(frame, (x,y), (x+bw, y+bh), (40,40,40), -1)
        fill = int((max(0, min(100, val)) / 100) * bw)
        if fill > 0:
            cv2.rectangle(frame, (x,y), (x+fill, y+bh), col, -1)

    eli_data = state.get("eli", {})
    eli      = eli_data.get("eli", 0)
    label    = eli_data.get("eli_label", "—")
    status   = eli_data.get("status", "—")
    emotion  = eli_data.get("dominant_emotion", "neutral")
    trend    = eli_data.get("eli_trend", "stable")

    ec = (80,200,80) if eli<30 else (80,200,200) if eli<50 else \
         (0,165,255) if eli<65 else (0,80,255) if eli<80 else (0,0,220)

    txt("Emora", 10, 28, (100,220,255), 0.75, True)

    cv2.putText(frame, f"{eli:.1f}", (10, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 2.0, ec, 3, cv2.LINE_AA)
    txt(label.upper(), 10, 128, ec, 0.42)
    bar(10, 136, 310, 12, eli, ec)

    sc = {"NORMAL":(80,200,80),"MASKING_DETECTED":(0,165,255),
          "CRISIS_RISK":(0,0,220)}.get(status,(180,180,180))
    txt(status, 10, 162, sc, 0.42)

    ta = "↑" if trend=="rising" else ("↓" if trend=="falling" else "→")
    tc = (0,80,220) if trend=="rising" else (80,200,80) if trend=="falling" else (150,150,150)
    txt(f"{ta} {trend.upper()}", 200, 162, tc, 0.38)

    ec2 = {"happy":(80,220,80),"neutral":(180,180,180),"sad":(220,130,60),
           "angry":(60,60,220),"fear":(180,60,180)}.get(emotion,(180,180,180))
    txt("EMOTION", 10, 188, (120,120,120), 0.38)
    txt(emotion.upper(), 10, 208, ec2, 0.58, True)

    if eli_data.get("contradiction_detected"):
        cv2.rectangle(frame, (8,216),(322,234),(0,60,160),-1)
        txt(f"CONTRADICTION: {eli_data.get('contradiction_type','').upper()}",
            12, 230, (255,255,80), 0.4)

    # Signals
    txt("SIGNALS", 10, 254, (120,120,120), 0.38)
    breakdown = eli_data.get("breakdown", {})
    signals = [
        ("Watch",  state.get("watch",{}).get("physio_score", 0),  "physio"),
        ("Face",   state.get("facial",{}).get("distress_score",0),"facial"),
        ("Voice",  state.get("voice",{}).get("combined_score",0), "voice"),
    ]
    y = 262
    for name, score, key in signals:
        active = breakdown.get(key, {}).get("active", False)
        bc = (80,200,80) if score<40 else (0,165,255) if score<65 else (0,80,255)
        txt(f"{name:<7}", 10, y+10, (160,160,160), 0.38)
        bar(65, y, 200, 11, score, bc if active else (50,50,50))
        txt(f"{score:.0f}", 272, y+10, bc if active else (80,80,80), 0.36)
        y += 18

    # Transcript — show what Whisper actually heard
    transcript = state.get("transcript", "")
    txt("HEARD", 10, y+16, (120,120,120), 0.38)
    display = (transcript[:36]+"...") if len(transcript)>36 else (transcript or "Listening...")
    txt(f'"{display}"', 10, y+32, (220,220,220), 0.38)

    # Agent response
    resp      = state.get("response", {})
    agent     = resp.get("agent", "—").upper()
    response  = resp.get("response", "")
    ac = {"CRISIS":(0,0,220),"GROUNDING":(0,165,255),"VALIDATION":(180,60,180),
          "CBT":(60,180,60),"SUPPORTIVE":(80,220,220)}.get(agent,(180,180,180))

    txt("AGENT", 10, y+58, (120,120,120), 0.38)
    txt(f"[{agent}]", 10, y+74, ac, 0.42, True)

    words   = response.split()
    lines   = []
    current = ""
    for word in words:
        if len(current + word) < 44:
            current += word + " "
        else:
            lines.append(current.strip())
            current = word + " "
    if current:
        lines.append(current.strip())

    ry = y + 90
    for line in lines[:4]:
        txt(line, 10, ry, (220,220,220), 0.36)
        ry += 15

    txt("Q / ESC to quit", 10, h-10, (70,70,70), 0.36)
    return frame


def main():
    print("\n" + "="*55)
    print("  Emora — Full System Test with Ollama")
    print("="*55 + "\n")

    print("Loading models...")
    facial_analyzer.warmup()
    voice_analyzer.warmup()
    load_whisper()
    print("All models ready ✓\n")

    for t, name in [
        (threading.Thread(target=voice_thread, daemon=True), "voice"),
        (threading.Thread(target=watch_thread, daemon=True), "watch"),
        (threading.Thread(target=eli_thread,   daemon=True), "eli"),
        (threading.Thread(target=llm_thread,   daemon=True), "llm"),
    ]:
        t.start()
        print(f"[{name}] thread started")

    time.sleep(2)

    cap = cv2.VideoCapture(0)
    for _ in range(30):
        cap.read()
    print("\nCamera ready ✓")
    print("Speak clearly into your mic — Whisper listens every 5 seconds\n")

    last_facial = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        now = time.time()

        if now - last_facial >= 2.0:
            facial_analyzer.analyze_frame(frame)
            state["facial"] = facial_analyzer.to_dict()
            last_facial = now

        frame = draw(frame, state)
        cv2.imshow("Emora — Full System", frame)

        if cv2.waitKey(30) & 0xFF in (ord('q'), ord('Q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()
    cv2.waitKey(1)
    print("\nDone ✓")


if __name__ == "__main__":
    main()