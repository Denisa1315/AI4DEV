from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3.1:8b", temperature=0.8, num_predict=150)

class SupportiveAgent:
    """General supportive conversation when ELI is moderate and no specific pattern detected."""

    def respond(self, emotion, eli, transcript, baseline_context="") -> dict:
        response = self._generate(emotion, eli, transcript, baseline_context)
        return {"response": response, "agent": "supportive", "emotion": emotion, "eli": eli}

    def _generate(self, emotion, eli, transcript, baseline_context):
        prompt = f"""You are AffectSync, a warm mental health companion for Indian users.
The user's stress level is {eli:.0f}/100. Emotion: {emotion}.
{f"Context: {baseline_context}" if baseline_context else ""}
They said: "{transcript or 'nothing yet'}"

Have a warm, natural supportive conversation.
Rules:
- Be genuinely curious about how they're doing
- No advice unless they ask
- Conversational, warm, like a good friend
- Respond ONLY to what the user actually said — do not invent context
- If they said nothing, ask one simple open question about how they are feeling
- Under 3 sentences. End with ONE open question."""

        try:
            return llm.invoke(prompt).strip()
        except:
            return ("It's really good to hear from you. "
                    "How has your day been going so far?")

supportive_agent = SupportiveAgent()