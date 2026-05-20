import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

import groq
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from groq import AsyncGroq
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from auth import verify_telegram_webapp

LOG_FORMAT = "%(levelname)s: %(message)s"
GROQ_API_KEY_ENV = "GROQ_API_KEY"
GROQ_API_KEY_ALIASES = ("groq_api_key",)
ALLOWED_ORIGINS_ENV = "ALLOWED_ORIGINS"
ALLOWED_ORIGINS_ALIASES = ("allowed_origins",)
DEFAULT_ALLOWED_ORIGINS = ("https://mandyfan10-stack.github.io",)

BASE_SYSTEM_PROMPT = (
    "Ты изящный и умный ИИ-репетитор по информатике (ОГЭ). "
    "Отвечай на русском языке кратко, дружелюбно, используй эмодзи по минимуму. "
    "Твоя цель — помочь ученику САМОМУ прийти к ответу через наводящие вопросы и объяснение теории. "
    "Не давай ответ напрямую."
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
TIMEOUT_REPLY = "Превышено время ожидания ответа от ИИ. Пожалуйста, попробуй позже."
GENERIC_ERROR_REPLY = "Произошла ошибка на сервере при обращении к ИИ. Пожалуйста, попробуй позже."

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
    configured_origins = [
        origin.strip().rstrip("/")
        for origin in origins.split(",")
        if origin.strip()
    ]
    if configured_origins:
        return configured_origins

    logger.warning(
        "ALLOWED_ORIGINS is not set — falling back to default origins including localhost. "
        "Set ALLOWED_ORIGINS in production to restrict access."
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
        logger.warning("Ключ %s не найден в Environment Variables.", GROQ_API_KEY_ENV)
        return None
    return AsyncGroq(api_key=api_key, timeout=10.0)


groq_client: Optional[AsyncGroq] = None


@asynccontextmanager
async def lifespan(app_: FastAPI):
    global groq_client
    groq_client = create_groq_client()
    logger.info("Приложение запущено. Groq: %s", "OK" if groq_client else "недоступен")
    yield
    if groq_client:
        try:
            await groq_client._client.aclose()
        except Exception:
            pass
    logger.info("Приложение остановлено.")


app = FastAPI(lifespan=lifespan)
allowed_origins = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Telegram-Init-Data"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"reply": RATE_LIMIT_REPLY})


app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


@app.get("/api/health")
async def health_check():
    if not groq_client:
        return JSONResponse(status_code=503, content={"status": "unavailable", "reason": "groq"})
    return {"status": "ok"}


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="User's chat message")
    history: Optional[list[ChatMessage]] = Field(default=None, max_length=20, description="Previous messages (max 20)")
    task_description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Task description from frontend (no correct answer)",
    )

    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


@app.post("/api/chat")
@limiter.limit("6/minute")
async def chat_endpoint(
    request: Request,
    req: ChatRequest,
    _auth: str = Depends(verify_telegram_webapp),
):
    if not groq_client:
        return JSONResponse(status_code=503, content={"reply": SERVICE_UNAVAILABLE_REPLY})

    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Запрос: %d chars", request_id, len(req.text))

    try:
        final_system_prompt = BASE_SYSTEM_PROMPT
        if req.task_description:
            final_system_prompt += (
                f"\n\nОПИСАНИЕ ЗАДАНИЯ:\n{req.task_description}"
            )

        messages = [{"role": "system", "content": final_system_prompt}]

        if req.history:
            for msg in req.history:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": f"Вопрос ученика: {req.text}"})

        stream = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            stream=True,
        )

        async def stream_generator(groq_stream):
            try:
                async def _inner():
                    async for chunk in groq_stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content

                gen = _inner()
                while True:
                    try:
                        content = await asyncio.wait_for(gen.__anext__(), timeout=30.0)
                        yield content
                    except StopAsyncIteration:
                        break
                    except asyncio.TimeoutError:
                        logger.warning("[%s] Таймаут стриминга Groq", request_id)
                        yield f"\n\n[{TIMEOUT_REPLY}]"
                        break
            except asyncio.CancelledError:
                logger.info("[%s] Клиент отключился во время стриминга.", request_id)
                raise
            except Exception:
                logger.exception("[%s] Ошибка стриминга Groq", request_id)
                yield f" [Ошибка: {GENERIC_ERROR_REPLY}]"
            finally:
                try:
                    await groq_stream.close()
                except Exception:
                    pass

        return StreamingResponse(stream_generator(stream), media_type="text/plain")

    except groq.RateLimitError:
        return JSONResponse(status_code=429, content={"reply": RATE_LIMIT_REPLY})
    except groq.APITimeoutError:
        logger.exception("[%s] Превышено время ожидания от API Groq.", request_id)
        return JSONResponse(status_code=504, content={"reply": TIMEOUT_REPLY})
    except groq.APIStatusError as e:
        logger.exception("[%s] API Groq вернул статус %s", request_id, e.status_code)
        return JSONResponse(status_code=503, content={"reply": SERVICE_UNAVAILABLE_REPLY})
    except Exception:
        logger.exception("[%s] Ошибка при обращении к API Groq.", request_id)
        return JSONResponse(status_code=500, content={"reply": GENERIC_ERROR_REPLY})
