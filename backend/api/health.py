"""
Health check endpoint — reports system status.
"""

from fastapi import APIRouter
from backend.services.llm_service import check_ollama
from backend.database.connection import check_db_connection
from backend.config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    """Return system health status for all components."""
    ollama_status = await check_ollama()
    db_connected = check_db_connection()

    return {
        "status": "ok" if (ollama_status["connected"] and db_connected) else "degraded",
        "ollama": {
            "url": settings.OLLAMA_URL,
            "connected": ollama_status["connected"],
            "model": ollama_status["model"],
            "model_available": ollama_status["model_available"],
        },
        "database": {
            "connected": db_connected,
            "type": "SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL",
        },
        "runtime": "Ollama",
        "slm": settings.OLLAMA_MODEL,
    }
