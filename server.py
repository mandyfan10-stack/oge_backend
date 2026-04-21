from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os
import logging
import groq
from groq import AsyncGroq
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

app = FastAPI()

# Configure CORS securely
# Get allowed origins from environment variable,
# defaulting to an empty list for security
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [
    origin.strip() for origin in allowed_origins_str.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' data: fastapi.tiangolo.com;"
    return response

# Подтягиваем ключ Groq из настроек Render
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    # Инициализация асинхронного клиента Groq
    client: Optional[AsyncGroq] = AsyncGroq(api_key=GROQ_API_KEY)
else:
    client = None
    print("ВНИМАНИЕ: Ключ GROQ_API_KEY не найден в Environment Variables!")


class ChatRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, max_length=2000, description="User's chat message"
    )


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not client:
        return {
            "reply": (
                "Ошибка сервера: API ключ GROQ_API_KEY не добавлен "
                "в настройки Render."
            )
        }

    try:
        # Системный промпт (поведение ИИ)
        system_prompt = (
            "Ты изящный и умный ИИ-репетитор по информатике (ОГЭ). "
            "Отвечай на русском языке кратко, дружелюбно, "
            "используй эмодзи по минимуму."
        )

        # Асинхронный запрос к сверхбыстрой модели Llama 3.3 через Groq
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Вопрос ученика: {req.text}"}
            ],
            temperature=0.7,
            max_tokens=1024,
        )

        return {"reply": response.choices[0].message.content}

    except groq.RateLimitError:
        return {
            "reply": (
                "Упс! Кажется, нейросеть сейчас немного перегружена "
                "запросами ⏳ Пожалуйста, подожди несколько секунд "
                "и попробуй снова!"
            )
        }
    except Exception:
        logging.exception("Детальная ошибка:")
        return {
            "reply": (
                "Произошла ошибка на сервере при обращении к ИИ. "
                "Проверь логи (Logs) на Render."
            )
        }
