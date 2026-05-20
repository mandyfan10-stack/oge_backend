import logging
import uuid

import groq
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import verify_telegram_webapp
from schemas import ChatRequest
from services.groq_service import build_messages, stream_groq

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

SERVICE_UNAVAILABLE_REPLY = "Ошибка сервера: Сервис временно недоступен."
RATE_LIMIT_REPLY = (
    "Упс! Кажется, нейросеть сейчас немного перегружена запросами ⏳ "
    "Пожалуйста, подожди несколько секунд и попробуй снова!"
)
TIMEOUT_REPLY = "Превышено время ожидания ответа от ИИ. Пожалуйста, попробуй позже."
GENERIC_ERROR_REPLY = "Произошла ошибка на сервере при обращении к ИИ. Пожалуйста, попробуй позже."


@router.post("/api/chat")
@limiter.limit("6/minute")
async def chat_endpoint(
    request: Request,
    req: ChatRequest,
    _auth: str = Depends(verify_telegram_webapp),
):
    from state import groq_client
    if not groq_client:
        return JSONResponse(status_code=503, content={"reply": SERVICE_UNAVAILABLE_REPLY})

    request_id = str(uuid.uuid4())[:8]
    logger.info("[%s] Запрос: %d chars", request_id, len(req.text))

    try:
        messages = build_messages(req.text, req.history, req.task_description)
        return StreamingResponse(
            stream_groq(groq_client, messages, request_id),
            media_type="text/plain",
        )
    except groq.RateLimitError:
        return JSONResponse(status_code=429, content={"reply": RATE_LIMIT_REPLY})
    except groq.APITimeoutError:
        logger.exception("[%s] Таймаут API Groq.", request_id)
        return JSONResponse(status_code=504, content={"reply": TIMEOUT_REPLY})
    except groq.APIStatusError as e:
        logger.exception("[%s] API Groq статус %s", request_id, e.status_code)
        return JSONResponse(status_code=503, content={"reply": SERVICE_UNAVAILABLE_REPLY})
    except Exception:
        logger.exception("[%s] Ошибка Groq.", request_id)
        return JSONResponse(status_code=500, content={"reply": GENERIC_ERROR_REPLY})
