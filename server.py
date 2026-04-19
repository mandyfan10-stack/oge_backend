from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from groq import Groq

app = FastAPI()

# Configure CORS securely
# Get allowed origins from environment variable, defaulting to an empty list for security
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подтягиваем ключ Groq из настроек Render
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    # Инициализация клиента Groq
    client = Groq(api_key=GROQ_API_KEY)
else:
    client = None
    print("ВНИМАНИЕ: Ключ GROQ_API_KEY не найден в Environment Variables!")

class ChatRequest(BaseModel):
    text: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "Ошибка сервера: API ключ GROQ_API_KEY не добавлен в настройки Render."}
        
    try:
        # Системный промпт (поведение ИИ)
        system_prompt = "Ты изящный и умный ИИ-репетитор по информатике (ОГЭ). Отвечай на русском языке кратко, дружелюбно, используй эмодзи по минимуму."
        
        # Запрос к сверхбыстрой модели Llama 3.3 через Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Вопрос ученика: {req.text}"}
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        
        return {"reply": response.choices[0].message.content}
        
    except Exception as e:
        error_msg = str(e)
        print(f"Детальная ошибка: {error_msg}")
        
        if "429" in error_msg or "rate limit" in error_msg.lower():
            return {"reply": "Упс! Кажется, нейросеть сейчас немного перегружена запросами ⏳ Пожалуйста, подожди несколько секунд и попробуй снова!"}
            
        return {"reply": f"Произошла ошибка на сервере при обращении к ИИ. Проверь логи (Logs) на Render."}
