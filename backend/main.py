"""
FastAPI application entry point.

Registers all routers, configures CORS, and initializes the database on startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database.connection import init_db
from backend.api import chat, tickets, services, files, health

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables. Shutdown: cleanup."""
    logger.info("Initializing database…")
    init_db()
    logger.info("ISLM backend ready.")
    yield
    logger.info("Shutting down ISLM backend.")


# ── App ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ISLM — Intelligent Service Level Management",
    description="Natural-language IT service management powered by DeepSeek-R1:1.5B",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow React dev server) ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(services.router)
app.include_router(files.router)


@app.get("/")
async def root():
    return {"message": "ISLM Backend is running", "docs": "/docs"}
