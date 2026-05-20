"""
FastAPI app factory + lifespan.

Business logic lives in:
  routes/chat.py   — POST /api/chat
  routes/health.py — GET  /api/health
  services/groq_service.py — streaming + prompt assembly
  schemas.py       — Pydantic request/response models
  auth.py          — Telegram WebApp HMAC verification
  state.py         — shared Groq client singleton
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import AsyncGroq
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import state
from routes.chat import router as chat_router
from routes.health import router as health_router

LOG_FORMAT = "%(levelname)s: %(message)s"
GROQ_API_KEY_ENV = "GROQ_API_KEY"
GROQ_API_KEY_ALIASES = ("groq_api_key",)
ALLOWED_ORIGINS_ENV = "ALLOWED_ORIGINS"
ALLOWED_ORIGINS_ALIASES = ("allowed_origins",)
DEFAULT_ALLOWED_ORIGINS = ("https://mandyfan10-stack.github.io",)

RATE_LIMIT_REPLY = (
    "Упс! Кажется, нейросеть сейчас немного перегружена запросами ⏳ "
    "Пожалуйста, подожди несколько секунд и попробуй снова!"
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "img-src 'self' data: fastapi.tiangolo.com;"
    ),
}

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def get_env(name: str, aliases: tuple[str, ...] = ()) -> str:
    for env_name in (name, *aliases):
        value = os.getenv(env_name)
        if value:
            return value
    return ""


def get_allowed_origins() -> list[str]:
    origins = get_env(ALLOWED_ORIGINS_ENV, ALLOWED_ORIGINS_ALIASES)
    configured = [o.strip().rstrip("/") for o in origins.split(",") if o.strip()]
    if configured:
        return configured
    logger.warning(
        "ALLOWED_ORIGINS not set — falling back to localhost defaults. "
        "Set ALLOWED_ORIGINS in production."
    )
    return list(DEFAULT_ALLOWED_ORIGINS) + [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:5173",
        "http://localhost:3000",
    ]


def create_groq_client() -> Optional[AsyncGroq]:
    api_key = get_env(GROQ_API_KEY_ENV, GROQ_API_KEY_ALIASES)
    if not api_key:
        logger.warning("Ключ %s не найден.", GROQ_API_KEY_ENV)
        return None
    return AsyncGroq(api_key=api_key, timeout=10.0)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    state.groq_client = create_groq_client()
    logger.info("Groq: %s", "OK" if state.groq_client else "недоступен")
    yield
    if state.groq_client:
        try:
            await state.groq_client._client.aclose()
        except Exception:
            pass
    logger.info("Приложение остановлено.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Telegram-Init-Data"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda req, exc: JSONResponse(status_code=429, content={"reply": RATE_LIMIT_REPLY}),
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


app.include_router(health_router)
app.include_router(chat_router)
