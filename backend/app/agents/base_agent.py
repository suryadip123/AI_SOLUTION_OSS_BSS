from langchain_ollama import ChatOllama
from app.config.settings import settings

def get_llm(temperature: float = 0.0):
    """Return a configured Ollama LLM instance."""
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=temperature,
    )
