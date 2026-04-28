import logging
import os
from typing import Any, Optional

import time

import groq
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import AsyncGroq
from pydantic import BaseModel, Field, field_validator

LOG_FORMAT = "%(levelname)s: %(message)s"
GROQ_API_KEY_ENV = "GROQ_API_KEY"
GROQ_API_KEY_ALIASES = ("groq_api_key",)
ALLOWED_ORIGINS_ENV = "ALLOWED_ORIGINS"
ALLOWED_ORIGINS_ALIASES = ("allowed_origins",)
DEFAULT_ALLOWED_ORIGINS = ("https://mandyfan10-stack.github.io",)

SYSTEM_PROMPT = (
    "Ты изящный и умный ИИ-репетитор по информатике (ОГЭ). "
    "Отвечай на русском языке кратко, дружелюбно, "
    "используй эмодзи по минимуму."
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

SERVICE_UNAVAILABLE_REPLY = "Ошибка сервера: Сервис временно недоступен."
RATE_LIMIT_REPLY = (
    "Упс! Кажется, нейросеть сейчас немного перегружена запросами ⏳ "
    "Пожалуйста, подожди несколько секунд и попробуй снова!"
)
TIMEOUT_REPLY = (
    "Превышено время ожидания ответа от ИИ. Пожалуйста, попробуй позже."
)
GENERIC_ERROR_REPLY = (
    "Произошла ошибка на сервере при обращении к ИИ. "
    "Пожалуйста, попробуй позже."
)

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def get_env(name: str, aliases: tuple[str, ...] = ()) -> str:
    for env_name in (name, *aliases):
        value = os.getenv(env_name)
        if value:
            if env_name != name:
                logger.warning(
                    "Используется переменная %s. Лучше переименовать ее в %s.",
                    env_name,
                    name,
                )
            return value

    return ""


def get_allowed_origins() -> list[str]:
    origins = get_env(ALLOWED_ORIGINS_ENV, ALLOWED_ORIGINS_ALIASES)
    configured_origins = [
        origin.strip().rstrip("/")
        for origin in origins.split(",")
        if origin.strip()
    ]

    return configured_origins or list(DEFAULT_ALLOWED_ORIGINS)


def create_groq_client() -> Optional[AsyncGroq]:
    api_key = get_env(GROQ_API_KEY_ENV, GROQ_API_KEY_ALIASES)

    if not api_key:
        logger.warning("Ключ %s не найден в Environment Variables.", GROQ_API_KEY_ENV)
        return None

    return AsyncGroq(api_key=api_key, timeout=10.0)


app = FastAPI()
allowed_origins = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ip_request_counts = {}
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 5
MAX_TRACKED_IPS = 10000


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value

    return response


client = create_groq_client()


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "ai_configured": client is not None,
        "cors_configured": bool(allowed_origins),
    }


class ChatRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's chat message",
    )

    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()

        return value


@app.post("/api/chat")
async def chat_endpoint(request: Request, req: ChatRequest):
    if not client:
        return {"reply": SERVICE_UNAVAILABLE_REPLY}

    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()

    # Prevent unbounded memory growth from millions of unique IPs (DoS protection)
    if len(ip_request_counts) > MAX_TRACKED_IPS:
        for ip in list(ip_request_counts.keys()):
            recent = [t for t in ip_request_counts[ip] if now - t < RATE_LIMIT_WINDOW]
            if not recent:
                del ip_request_counts[ip]
            else:
                ip_request_counts[ip] = recent
        if len(ip_request_counts) > MAX_TRACKED_IPS:
            ip_request_counts.clear()

    history = ip_request_counts.get(client_ip, [])
    history = [t for t in history if now - t < RATE_LIMIT_WINDOW]

    if len(history) >= RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(status_code=429, content={"reply": RATE_LIMIT_REPLY})

    history.append(now)
    ip_request_counts[client_ip] = history

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Вопрос ученика: {req.text}"},
            ],
            temperature=0.7,
            max_tokens=1024,
        )

        return {"reply": response.choices[0].message.content}

    except groq.RateLimitError:
        return {"reply": RATE_LIMIT_REPLY}
    except groq.APITimeoutError:
        logger.exception("Превышено время ожидания от API Groq.")
        return {"reply": TIMEOUT_REPLY}
    except Exception:
        logger.exception("Ошибка при обращении к API Groq.")
        return {"reply": GENERIC_ERROR_REPLY}
