# services/agents/crisis_agent.py
#
# Crisis agent — never uses LLM.
# When ELI status is CRISIS_RISK or crisis language detected,
# this agent responds immediately with escalation resources.
# LLM is intentionally NOT used here — too slow, too unpredictable.

import random

CRISIS_RESPONSES = [
    (
        "I can hear that things feel really overwhelming right now. "
        "You don't have to carry this alone. "
        "Please reach out to iCall right now — they're available 24/7 at 9152987821. "
        "Would you like me to stay with you while you call?"
    ),
    (
        "What you're feeling right now sounds really painful, and I want you to know that matters. "
        "Please contact iCall at 9152987821 — they're trained to help with exactly this. "
        "You deserve support beyond what I can offer."
    ),
    (
        "I'm concerned about you right now. "
        "iCall is available 24/7 at 9152987821 and they speak Hindi and English. "
        "Please reach out to them — this is important."
    ),
]

VANDREVALA_RESPONSE = (
    "Please reach out to the Vandrevala Foundation helpline: 1860-2662-345. "
    "They're available 24/7, free of charge, and completely confidential."
)

SNEHI_RESPONSE = (
    "SNEHI is also available at +91-44-24640050 if you'd prefer to talk to someone right now."
)


class CrisisAgent:
    """
    Handles crisis situations.
    Never uses LLM — always returns pre-written escalation response.
    Fast, reliable, no hallucination risk.
    """

    def respond(
        self,
        trigger: str = "high_signals",   # high_signals / crisis_language / user_request
        transcript: str = ""
    ) -> dict:
        """
        Returns crisis response with resources.

        trigger options:
          high_signals    — ELI or any signal > 85
          crisis_language — Whisper detected crisis words
          user_request    — user explicitly asked for help
        """
        primary = random.choice(CRISIS_RESPONSES)

        return {
            "response":        primary,
            "agent":           "crisis",
            "trigger":         trigger,
            "resources": {
                "iCall":        "9152987821",
                "Vandrevala":   "1860-2662-345",
                "SNEHI":        "+91-44-24640050",
                "iCall_website":"https://icallhelpline.org",
            },
            "show_resources":  True,
            "block_further_chat": False,   # keep chat open so user isn't alone
        }


crisis_agent = CrisisAgent()