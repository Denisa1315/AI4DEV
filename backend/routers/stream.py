from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.agents.therapy_router import CRISIS_WORDS
from services.ml.baseline_model import baseline_model
from langchain_ollama import OllamaLLM
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4)

# SSE response headers — disable all buffering layers
SSE_HEADERS = {
    "X-Accel-Buffering": "no",   # nginx
    "Cache-Control":     "no-cache",
    "Connection":        "keep-alive",
}

router = APIRouter(prefix="/api")

llm = OllamaLLM(model="llama3.1:8b", temperature=0.7, num_predict=200)


def build_prompt(eli_payload: dict) -> str:
    eli        = eli_payload.get("eli", 50)
    status     = eli_payload.get("status", "NORMAL")
    emotion    = eli_payload.get("dominant_emotion", "neutral")
    transcript = eli_payload.get("transcript", "").strip()
    contra     = eli_payload.get("contradiction_detected", False)
    contra_type= eli_payload.get("contradiction_type", "none")
    user_id    = eli_payload.get("user_id", "demo_user")

    # Crisis language check
    if transcript and any(w in transcript.lower() for w in CRISIS_WORDS):
        return None, "crisis", (
            "I hear you, and what you're feeling matters deeply. "
            "Please reach out to iCall right now — 9152987821, available 24/7. "
            "You don't have to carry this alone."
        )

    if status == "CRISIS_RISK" or contra_type == "CRISIS":
        return None, "crisis", (
            "I can hear that things feel really overwhelming right now. "
            "Please reach out to iCall — 9152987821, available 24/7. "
            "You deserve support beyond what I can offer."
        )

    # Baseline context
    deviation = baseline_model.get_deviation(user_id=user_id, eli=eli)
    baseline_context = deviation.context_message if deviation.is_calibrated else ""

    # ── Text-based masking detection ────────────────────────────────────────────
    # voice_analysis.py only sees audio from the mic loop — chat text never
    # passes through it, so contradiction_detected is always False for chat.
    # We replicate the same logic here using the transcript + facial emotion.
    FINE_WORDS = {
        "fine", "okay", "ok", "alright", "good", "great", "well",
        "nothing", "fine thanks", "i'm fine", "im fine", "all good",
    }
    DISTRESS_FACES = {"sad", "angry", "fear", "disgust", "contempt"}

    if transcript and not contra:
        t_lower = transcript.lower()
        words   = set(t_lower.split())
        says_fine = bool(words & FINE_WORDS) or any(
            p in t_lower for p in ["i am fine", "i'm fine", "everything is okay",
                                   "i am okay", "nothing happened", "don't worry",
                                   "it's fine", "its fine", "everything's fine"]
        )
        face_distressed = emotion in DISTRESS_FACES
        if says_fine and face_distressed and eli > 35:
            contra      = True
            contra_type = "masking"

    # Determine approach — face emotion is the PRIMARY signal, ELI is secondary
    if contra and contra_type == "masking":
        approach = "masking"
    elif emotion in ("angry", "fear") and eli > 30:   # face is enough
        approach = "grounding"
    elif emotion == "sad":                              # any ELI — face says sad
        approach = "validation"
    elif emotion in ("disgust", "contempt") and eli > 40:
        approach = "validation"
    elif transcript and any(p in transcript.lower() for p in [
        "don't like my life", "hate my life", "feeling bad",
        "not feeling good", "i'm sad", "i am sad", "so sad",
    ]):
        approach = "validation"
    elif transcript and any(w in transcript.lower() for w in [
        "always", "never", "everyone", "nobody", "worst",
        "terrible", "my fault", "i failed", "should", "useless",
    ]) and eli > 35:
        approach = "cbt"
    else:
        approach = "supportive"


    prompts = {
        "masking": f"""You are Emora, a warm mental health companion.
The user said: "{transcript or 'I am fine'}"
But their stress signals show ELI={eli:.0f}/100, emotion={emotion}.
Gently acknowledge what they said WITHOUT confronting them.
Show you notice something might be weighing on them.
Under 2 sentences. End with a soft open question.
Respond ONLY in English.""",

        "grounding": f"""You are Emora, a warm mental health companion.
The user said: "{transcript or 'nothing'}"
They appear {emotion} with stress level {eli:.0f}/100.
Acknowledge how they feel in ONE sentence.
Suggest box breathing (breathe in 4, hold 4, out 4, hold 4) naturally.
Under 2 sentences. End with "Want to try it together?"
Respond ONLY in English.""",

        "validation": f"""You are Emora, a warm mental health companion.
The user said: "{transcript or 'nothing'}"
They appear sad or low with stress level {eli:.0f}/100.
{f"Context: {baseline_context}" if baseline_context else ""}
Make them feel heard. Do NOT give advice or solutions.
Reflect back their feeling in your own words.
Under 2 sentences. End with one open question.
Respond ONLY in English. Do not start with "I".""",

        "cbt": f"""You are Emora, a warm mental health companion.
The user said: "{transcript}"
They appear to be thinking negatively. Stress: {eli:.0f}/100.
Acknowledge what they said in ONE sentence.
Ask ONE gentle Socratic question to help them see it differently.
No clinical words. Under 2 sentences.
Respond ONLY in English.""",

        "supportive": f"""You are Emora, a warm mental health companion.
The user said: "{transcript or 'nothing yet'}"
Their current emotional state: {emotion}. Stress level: {eli:.0f}/100.
{f"Context: {baseline_context}" if baseline_context else ""}
IMPORTANT: If the emotion is sad, angry, fear or disgust, do NOT respond with positivity or cheerfulness.
Acknowledge the emotional tone you observe. Respond with warmth and empathy.
Under 2 sentences. End with one open question.
Respond ONLY in English.""",
    }

    return prompts[approach], approach, None


@router.post("/chat/stream")
async def chat_stream(body: dict):
    """
    Streaming /api/chat via Server-Sent Events.
    Each SSE frame:  data: <token>\n\n
    End frame:       data: [DONE]\n\n
    Mode frame:      data: [META]<mode>[/META]\n\n
    """
    eli_payload = body.get("eli_payload", {})
    message     = body.get("message", "").strip()
    if message and not eli_payload.get("transcript"):
        eli_payload["transcript"] = message

    prompt, approach, static_response = build_prompt(eli_payload)

    # ── Crisis path — static text, streamed word-by-word ──
    if static_response is not None:
        async def crisis_stream():
            for i, word in enumerate(static_response.split()):
                sep = " " if i < len(static_response.split()) - 1 else ""
                yield f"data: {word}{sep}\n\n"
                await asyncio.sleep(0.04)
            yield f"data: [DONE]\n\n"
            yield f"data: [META]{approach or 'crisis'}[/META]\n\n"

        return StreamingResponse(crisis_stream(), media_type="text/event-stream", headers=SSE_HEADERS)

    # ── LLM path — real streaming via thread pool + queue ──
    #
    # llm.stream() is a SYNC generator.  Running it directly inside an async
    # generator blocks the event loop between tokens, which causes uvicorn to
    # batch them all and only flush when the loop resumes — making the response
    # appear non-streaming.
    #
    # Fix: push tokens onto an asyncio.Queue from a ThreadPoolExecutor thread.
    # The async generator below awaits each token individually, yielding each
    # SSE frame the instant it arrives.
    async def llm_stream():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def run_sync():
            try:
                for chunk in llm.stream(prompt):
                    token = str(chunk)
                    if token:
                        loop.call_soon_threadsafe(queue.put_nowait, token)
            except Exception as e:
                print(f"[Stream] LLM error in thread: {e}")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        loop.run_in_executor(_executor, run_sync)

        try:
            while True:
                token = await queue.get()
                if token is None:
                    break
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
        except Exception as e:
            print(f"[Stream] Generator error: {e}")
            yield f"data: I'm here with you. How are you feeling?\n\n"

        yield f"data: [DONE]\n\n"
        yield f"data: [META]{approach}[/META]\n\n"

    return StreamingResponse(llm_stream(), media_type="text/event-stream", headers=SSE_HEADERS)

