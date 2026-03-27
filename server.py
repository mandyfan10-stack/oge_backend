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
    # Инициализация нового клиента Google GenAI
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
        
        # Запрос к самой современной модели
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return {"reply": response.text}
    except Exception as e:
        print(f"Детальная ошибка: {str(e)}")
        return {"reply": "Произошла ошибка на сервере при обращении к ИИ. Проверь логи (Logs) на Render."}
