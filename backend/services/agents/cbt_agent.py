from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3.1:8b", temperature=0.65, num_predict=150)

DISTORTION_SIGNALS = {
    "all_or_nothing":    ["always", "never", "everyone", "nobody", "everything", "nothing"],
    "catastrophising":   ["worst", "terrible", "disaster", "ruined", "horrible", "awful"],
    "mind_reading":      ["they think", "he thinks", "she thinks", "they hate"],
    "should_statements": ["should", "must", "have to", "supposed to", "ought to"],
    "self_blame":        ["my fault", "i failed", "i ruined", "i messed up", "i'm useless", "i'm stupid"],
}

class CBTAgent:
    def respond(self, emotion, eli, transcript, baseline_context="") -> dict:
        distortion = self._detect(transcript)
        response   = self._generate(emotion, eli, transcript, distortion)
        return {"response": response, "agent": "cbt",
                "distortion": distortion, "emotion": emotion, "eli": eli}

    def _detect(self, transcript):
        if not transcript:
            return "general_negative"
        t = transcript.lower()
        for distortion, keywords in DISTORTION_SIGNALS.items():
            if any(kw in t for kw in keywords):
                return distortion
        return "general_negative"

    def _generate(self, emotion, eli, transcript, distortion):
        context_map = {
            "all_or_nothing":    "using absolute thinking (always/never)",
            "catastrophising":   "imagining the worst possible outcome",
            "mind_reading":      "assuming what others think",
            "should_statements": "putting a lot of pressure on themselves",
            "self_blame":        "blaming themselves very harshly",
            "general_negative":  "thinking in a very negative pattern",
        }
        context = context_map.get(distortion, "thinking negatively")

        prompt = f"""You are Emora, a warm mental health companion for Indian users.
The user appears to be {context}.
Stress: {eli:.0f}/100. Emotion: {emotion}.
They said: "{transcript or 'nothing yet'}"

Use ONE gentle Socratic question to help them examine this thought.
Rules:
- Never tell them they're wrong or irrational
- No clinical words (CBT, cognitive, distortion, therapy)
- Ask ONE gentle question that opens up their thinking
- Be warm and curious, not clinical
- Respond ONLY to what the user actually said — do not invent context
- If they said nothing, ask one simple open question about how they are feeling
- Under 3 sentences. Acknowledge what they said first."""

        try:
            return llm.invoke(prompt).strip()
        except:
            return ("That sounds like a really heavy thought to carry. "
                    "When you think about this situation, is there any part "
                    "that's gone differently than you expected?")

cbt_agent = CBTAgent()