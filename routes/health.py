from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/health")
async def health_check():
    from state import groq_client
    if not groq_client:
        return JSONResponse(status_code=503, content={"status": "unavailable", "reason": "groq"})
    return {"status": "ok"}
