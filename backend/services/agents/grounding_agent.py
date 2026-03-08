# services/agents/grounding_agent.py
#
# Grounding agent — used when:
#   - Dominant emotion is angry or fear
#   - ELI > 65 and rising
#   - User needs immediate de-escalation before deeper work

from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3.1:8b", temperature=0.7, num_predict=150)

GROUNDING_TECHNIQUES = {
    "box_breathing": {
        "name": "Box Breathing",
        "steps": [
            "Breathe in slowly for 4 counts",
            "Hold for 4 counts",
            "Breathe out for 4 counts",
            "Hold for 4 counts",
            "Repeat 3 times"
        ],
        "duration": "2 minutes",
        "best_for": ["angry", "fear"],
    },
    "five_four_three": {
        "name": "5-4-3-2-1 Grounding",
        "steps": [
            "Name 5 things you can SEE right now",
            "Name 4 things you can TOUCH",
            "Name 3 things you can HEAR",
            "Name 2 things you can SMELL",
            "Name 1 thing you can TASTE",
        ],
        "duration": "3 minutes",
        "best_for": ["fear", "panic"],
    },
    "cold_water": {
        "name": "Temperature Reset",
        "steps": [
            "Go to a tap and run cold water",
            "Place your wrists under the cold water for 30 seconds",
            "Focus entirely on the sensation of the cold",
            "Take 3 slow deep breaths",
        ],
        "duration": "1 minute",
        "best_for": ["angry", "overwhelmed"],
    },
}


class GroundingAgent:
    """
    Grounding agent for acute stress, anger, and anxiety.
    LLM generates warm contextual intro + structured technique shown as steps.
    """

    def respond(
        self,
        emotion:          str,
        eli:              float,
        transcript:       str,
        baseline_context: str = "",
    ) -> dict:
        technique = self._pick_technique(emotion, eli)
        intro     = self._generate_intro(emotion, eli, transcript, technique)
        return {
            "response":   intro,
            "agent":      "grounding",
            "technique":  technique,
            "show_steps": True,
            "emotion":    emotion,
            "eli":        eli,
        }

    def _pick_technique(self, emotion: str, eli: float) -> dict:
        if emotion == "angry":
            return GROUNDING_TECHNIQUES["cold_water"] \
                if eli > 75 else GROUNDING_TECHNIQUES["box_breathing"]
        elif emotion in ("fear", "surprise"):
            return GROUNDING_TECHNIQUES["five_four_three"]
        else:
            return GROUNDING_TECHNIQUES["box_breathing"]

    def _generate_intro(self, emotion, eli, transcript, technique) -> str:
        emotion_context = {
            "angry":   "feeling frustrated or angry",
            "fear":    "feeling anxious or scared",
            "sad":     "feeling overwhelmed",
            "surprise":"feeling caught off guard",
        }.get(emotion, "feeling stressed")

        prompt = f"""You are AffectSync, a warm mental health companion for Indian users.

The user appears to be {emotion_context} (stress level: {eli:.0f}/100).
They said: "{transcript if transcript else 'nothing yet'}"

Write ONE warm sentence acknowledging how they feel.
Then naturally suggest the {technique['name']} technique in one sentence.
Do NOT list steps. Do NOT use clinical words like therapy or disorder.
Keep it under 3 sentences. End with a gentle question.
Respond ONLY to what the user actually said — do not invent context
If they said nothing, ask one simple open question about how they are feeling
Write like a caring friend, not a doctor."""

        try:
            return llm.invoke(prompt).strip()
        except Exception as e:
            print(f"[GroundingAgent] LLM error: {e}")
            return (
                f"It sounds like things feel intense right now — that's completely okay. "
                f"Let's try {technique['name']} together, it only takes a couple of minutes. "
                f"Would you like to try it now?"
            )


grounding_agent = GroundingAgent()