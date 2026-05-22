import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/health")
async def health_check():
    from state import groq_client
    payload = {
        "status": "ok" if groq_client else "unavailable",
        "groq": bool(groq_client),
        "telegram_token_set": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "allowed_origins_set": bool(os.getenv("ALLOWED_ORIGINS")),
    }
    if not groq_client:
        return JSONResponse(
            status_code=503,
            content={**payload, "reason": "groq"},
        )
    return payload
