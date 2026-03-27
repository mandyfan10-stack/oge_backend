from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import os

app = FastAPI()

# Разрешаем запросы с твоего сайта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подтягиваем ключ из настроек Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    # Инициализация клиента Google GenAI
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None
    print("ВНИМАНИЕ: Ключ GEMINI_API_KEY не найден в Environment Variables!")

class ChatRequest(BaseModel):
    text: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "Ошибка сервера: API ключ не добавлен в настройки Render."}
        
    try:
        prompt = f"Ты изящный и умный ИИ-репетитор по информатике (ОГЭ). Отвечай кратко, дружелюбно, используй эмодзи по минимуму.\n\nВопрос ученика: {req.text}"
        
        # АЛЬТЕРНАТИВА: Используем gemini-1.5-flash (У нее огромные бесплатные лимиты - 1500 запросов в день!)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        return {"reply": response.text}
    except Exception as e:
        error_msg = str(e)
        print(f"Детальная ошибка: {error_msg}")
        
        # Красивая обработка ошибки 429 для пользователя
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return {"reply": "Упс! Кажется, нейросеть сейчас немного перегружена запросами ⏳ Пожалуйста, подожди около минуты и попробуй снова!"}
            
        return {"reply": "Произошла ошибка на сервере при обращении к ИИ. Проверь логи (Logs) на Render."}
