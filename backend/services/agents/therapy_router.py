# services/agents/therapy_router.py

from langchain_ollama import OllamaLLM
from services.ml.baseline_model import baseline_model
from services.agents.crisis_agent import crisis_agent

llm = OllamaLLM(model="llama3.1:8b", temperature=0.7, num_predict=200)

CRISIS_WORDS = {
    "die", "suicide", "kill myself", "end it", "hopeless",
    "worthless", "give up", "no point", "wanna die", "want to die",
    "don't want to live", "cant go on", "can't go on",
    "not worth living", "end my life", "kill me", "i want to die"
}

def route(eli_payload: dict, user_id: str = "demo_user") -> dict:
    eli        = eli_payload.get("eli", 50)
    status     = eli_payload.get("status", "NORMAL")
    emotion    = eli_payload.get("dominant_emotion", "neutral")
    transcript = eli_payload.get("transcript", "").strip()
    contra     = eli_payload.get("contradiction_detected", False)
    contra_type= eli_payload.get("contradiction_type", "none")

    # ── 1. Crisis language — ALWAYS first, regardless of ELI ──
    if transcript and any(w in transcript.lower() for w in CRISIS_WORDS):
        return {
            "response": (
                "I hear you, and what you're feeling matters deeply. "
                "Please reach out to iCall right now — 9152987821, available 24/7. "
                "You don't have to carry this alone."
            ),
            "agent": "crisis",
            "resources": {"iCall": "9152987821", "Vandrevala": "1860-2662-345"},
            "show_resources": True,
        }

    # ── 2. Crisis signals from fusion engine ──────────────────
    if status == "CRISIS_RISK" or contra_type == "CRISIS":
        return {
            "response": (
                "I can hear that things feel really overwhelming right now. "
                "Please reach out to iCall — 9152987821, available 24/7. "
                "You deserve support beyond what I can offer."
            ),
            "agent": "crisis",
            "resources": {"iCall": "9152987821", "Vandrevala": "1860-2662-345"},
            "show_resources": True,
        }

    # Get baseline context
    deviation        = baseline_model.get_deviation(user_id=user_id, eli=eli)
    baseline_context = deviation.context_message if deviation.is_calibrated else ""

    # ── 3. Masking ────────────────────────────────────────────
    if contra and contra_type == "masking":
        approach = "masking"

    # ── 4. Angry or fear + elevated ───────────────────────────
    elif emotion in ("angry", "fear") and eli > 55:
        approach = "grounding"

    # ── 5. Sad + elevated ─────────────────────────────────────
    elif emotion == "sad" and eli > 45:
        approach = "validation"

    # ── 6. Negative phrases in transcript ─────────────────────
    elif transcript and any(p in transcript.lower() for p in [
        "don't like my life", "hate my life", "feeling bad",
        "not feeling good", "everything is bad", "very bad",
        "feel terrible", "feel awful", "feel horrible",
        "i'm sad", "i am sad", "so sad", "really sad",
    ]):
        approach = "validation"

    # ── 7. Cognitive distortions ──────────────────────────────
    elif transcript and any(w in transcript.lower() for w in [
        "always", "never", "everyone", "nobody", "worst",
        "terrible", "my fault", "i failed", "should", "useless",
        "nothing works", "no one cares", "nobody cares",
        "everything is wrong", "i can't do anything",
    ]) and eli > 40:
        approach = "cbt"

    # ── 8. General supportive ──────────────────────────────────
    else:
        approach = "supportive"

    # Build prompt
    prompts = {
        "masking": f"""You are AffectSync, a warm mental health companion.
The user said: "{transcript or 'I am fine'}"
But their stress signals show ELI={eli:.0f}/100, emotion={emotion}.
Gently acknowledge what they said WITHOUT confronting them.
Show you notice something might be weighing on them.
Under 2 sentences. End with a soft open question.
Respond ONLY in English.""",

        "grounding": f"""You are AffectSync, a warm mental health companion.
The user said: "{transcript or 'nothing'}"
They appear {emotion} with stress level {eli:.0f}/100.
Acknowledge how they feel in ONE sentence.
Suggest box breathing (breathe in 4, hold 4, out 4, hold 4) naturally.
Under 2 sentences. End with "Want to try it together?"
Respond ONLY in English.""",

        "validation": f"""You are AffectSync, a warm mental health companion.
The user said: "{transcript or 'nothing'}"
They appear sad or low with stress level {eli:.0f}/100.
{f"Context: {baseline_context}" if baseline_context else ""}
Make them feel heard. Do NOT give advice or solutions.
Reflect back their feeling in your own words.
Under 2 sentences. End with one open question.
Respond ONLY in English. Do not start with "I".""",

        "cbt": f"""You are AffectSync, a warm mental health companion.
The user said: "{transcript}"
They appear to be thinking negatively. Stress: {eli:.0f}/100.
Acknowledge what they said in ONE sentence.
Ask ONE gentle Socratic question to help them see it differently.
No clinical words. Under 2 sentences.
Respond ONLY in English.""",

        "supportive": f"""You are AffectSync, a warm mental health companion.
The user said: "{transcript or 'nothing yet'}"
Stress level: {eli:.0f}/100. Emotion: {emotion}.
{f"Context: {baseline_context}" if baseline_context else ""}
Respond warmly to exactly what they said.
If they said nothing, ask how they are feeling right now.
Under 2 sentences. End with one open question.
Respond ONLY in English.""",
    }

    try:
        response = llm.invoke(prompts[approach]).strip()
    except Exception as e:
        print(f"[Router] LLM error: {e}")
        response = "I'm here with you. How are you feeling right now?"

    return {
        "response":          response,
        "agent":             approach,
        "emotion":           emotion,
        "eli":               eli,
        "transcript_heard":  transcript,
    }