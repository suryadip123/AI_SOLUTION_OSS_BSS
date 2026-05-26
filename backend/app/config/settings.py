from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "AI Solution OSS-BSS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Ollama
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # SQLite
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/telecom.db"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://frontend:5173"]

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
