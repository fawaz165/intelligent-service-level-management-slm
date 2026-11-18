import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    _DEFAULT_DB_FILE: str = (BASE_DIR / "islm_recovered.db").as_posix()

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{_DEFAULT_DB_FILE}"
    )

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://", "postgresql+psycopg://", 1
        )
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

    OLLAMA_URL: str = os.getenv(
        "OLLAMA_URL", "http://localhost:11434"
    )
    OLLAMA_MODEL: str = os.getenv(
        "OLLAMA_MODEL", "deepseek-r1:1.5b"
    )

    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))

    ALLOWED_FILE_TYPES: list[str] = os.getenv(
        "ALLOWED_FILE_TYPES",
        ".pdf,.doc,.docx,.txt,.csv,.xlsx,.png,.jpg,.jpeg,.log,.json,.xml",
    ).split(",")

    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

    @classmethod
    def storage_dir(cls) -> Path:
        p = Path(cls.STORAGE_PATH).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()