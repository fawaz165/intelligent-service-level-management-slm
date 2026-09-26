"""
Application configuration — reads from .env and provides typed settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Centralized application settings."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./islm.db")

    # Ollama / LLM
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")

    # File storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_FILE_TYPES: list[str] = os.getenv(
        "ALLOWED_FILE_TYPES",
        ".pdf,.doc,.docx,.txt,.csv,.xlsx,.png,.jpg,.jpeg,.log,.json,.xml",
    ).split(",")

    # Derived
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

    @classmethod
    def storage_dir(cls) -> Path:
        """Return the resolved storage directory, creating it if needed."""
        p = Path(cls.STORAGE_PATH).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
