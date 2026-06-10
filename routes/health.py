import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.groq_service import get_model

router = APIRouter()


@router.get("/")
async def root():
    """Friendly landing payload instead of a bare 404 — useful when the
    Render URL is opened in a browser to eyeball that the service is up."""
    return {
        "service": "oge-backend",
        "description": "API ИИ-репетитора OGE-Bot (информатика ОГЭ)",
        "health": "/api/health",
    }


@router.get("/api/health")
async def health_check():
    from state import groq_client
    payload = {
        "status": "ok" if groq_client else "unavailable",
        "groq": bool(groq_client),
        "model": get_model(),
        "telegram_token_set": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "allowed_origins_set": bool(os.getenv("ALLOWED_ORIGINS")),
    }
    if not groq_client:
        return JSONResponse(
            status_code=503,
            content={**payload, "reason": "groq"},
        )
    return payload
