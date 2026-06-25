import time
import requests
from langchain_ollama import ChatOllama

# Pulling the model llm on terminal to your enviroment: docker exec ollama ollama pull llama3:8b

DEFAULT_BASE_URL   = "http://localhost:11434"
DEFAULT_MODEL      = "llama3:8b"
DEFAULT_MAX_TOKENS = 120
DEFAULT_CONTEXT    = 1024

def wait_for_ollama(base_url: str, timeout_seconds: int = 120) -> bool:
    for _ in range(timeout_seconds):
        try:
            r = requests.get(f"{base_url}/api/tags", timeout=2)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def create_local_llm(base_url: str = DEFAULT_BASE_URL,model: str = DEFAULT_MODEL,temperature: float = 0,
                    max_tokens: int = DEFAULT_MAX_TOKENS, max_context: int = DEFAULT_CONTEXT):

    print("⏳ Waiting for Ollama server...")

    if not wait_for_ollama(base_url):
        raise RuntimeError("❌ Ollama server is not available")

    print("✅ Ollama is ready!")

    ollama = ChatOllama(
        base_url=base_url,
        model=model,
        temperature=temperature,
        model_kwargs={"num_predict": max_tokens,"num_ctx": max_context}
    )

    return ollama

