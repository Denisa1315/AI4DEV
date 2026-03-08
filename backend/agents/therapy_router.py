from langchain_community.llms import Ollama
from services.ml.baseline_model import baseline_model

llm = Ollama(model="llama3.1:8b")

def route_therapy(eli_result, voice_data, user_id="demo_user") -> str:
    """
    Route to correct therapy approach based on ELI result.
    Uses your fusion engine output directly.
    """
    eli        = eli_result["eli"]
    status     = eli_result["status"]
    emotion    = eli_result["dominant_emotion"]
    transcript = eli_result["transcript"]
    contra     = eli_result["contradiction_detected"]
    contra_type= eli_result["contradiction_type"]

    # Crisis — do not pass to LLM, escalate immediately
    if status == "CRISIS_RISK" or contra_type == "CRISIS":
        return (
            "I can hear that things feel very overwhelming right now. "
            "Please reach out to iCall immediately — they're available "
            "24/7 at 9152987821. You don't have to face this alone."
        )

    # Get baseline context
    deviation = baseline_model.get_deviation(
        user_id      = user_id,
        eli          = eli,
    )

    # Build system prompt based on emotion + status
    if contra and contra_type == "masking":
        approach = "contradiction"
    elif emotion in ("sad", "fear") and eli > 60:
        approach = "validation"
    elif emotion == "angry":
        approach = "grounding"
    elif eli > 70:
        approach = "cbt"
    else:
        approach = "supportive"

    system_prompt = _build_system_prompt(
        approach, eli, emotion, deviation.context_message
    )

    response = llm.invoke(
        system_prompt + f"\n\nUser said: '{transcript}'"
    )
    return response

def _build_system_prompt(approach, eli, emotion, baseline_context):
    base = f"""You are AffectSync, a culturally aware mental health companion for Indian users.
Current state: ELI={eli:.0f}/100, dominant emotion={emotion}
Baseline context: {baseline_context}

Rules:
- Never diagnose
- Never use clinical jargon
- Use warm conversational Hindi-English mix if appropriate
- Keep response under 3 sentences
- End with one open question
"""
    approaches = {
        "contradiction": base + "The user says they're fine but their body signals show stress. Gently acknowledge the mismatch without confronting them directly.",
        "validation":    base + "User appears sad or fearful. Validate their feelings first before anything else. Do not rush to solutions.",
        "grounding":     base + "User appears angry or very stressed. Guide them toward a simple grounding exercise — 5-4-3-2-1 or box breathing.",
        "cbt":           base + "User shows signs of cognitive distortion. Use gentle Socratic questioning to examine their thoughts.",
        "supportive":    base + "User needs general support. Be warm, curious, and present. Ask how their day has been.",
    }
    return approaches.get(approach, approaches["supportive"])