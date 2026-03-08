from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3.1:8b", temperature=0.75, num_predict=150)

class ValidationAgent:
    def respond(self, emotion, eli, transcript, baseline_context="") -> dict:
        response = self._generate(emotion, eli, transcript, baseline_context)
        return {"response": response, "agent": "validation", "emotion": emotion, "eli": eli}

    def _generate(self, emotion, eli, transcript, baseline_context):
        prompt = f"""You are Emora, a warm empathetic mental health companion for Indian users.
The user appears sad or low (stress level: {eli:.0f}/100).
{f"Context: {baseline_context}" if baseline_context else ""}
They said: "{transcript or 'nothing yet'}"

Your ONLY job is to make them feel heard.
Rules:
- Do NOT give advice or solutions
- Do NOT say "I understand" — show it instead  
- Reflect back what they seem to be feeling in your own words
- Warm conversational language — like a trusted friend
- Under 3 sentences. End with ONE open question.
- Respond ONLY to what the user actually said — do not invent context
- If they said nothing, ask one simple open question about how they are feeling
- Do not start your response with "I"."""

        try:
            return llm.invoke(prompt).strip()
        except:
            return ("That sounds really tough, and it makes sense you'd feel that way. "
                    "Sometimes things just pile up and become a lot to carry. "
                    "What's been weighing on you the most?")

validation_agent = ValidationAgent()