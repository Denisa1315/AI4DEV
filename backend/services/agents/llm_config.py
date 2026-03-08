from langchain_ollama import OllamaLLM

llm = OllamaLLM(
    model       = "llama3.1:8b",
    temperature = 0.7,
    num_predict = 150,
)

llm_fast = OllamaLLM(
    model       = "llama3.1:8b",
    temperature = 0.2,
    num_predict = 30,
)

print("[LLM] Ollama llama3.1:8b ready ✓")