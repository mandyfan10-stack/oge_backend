from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os

app = FastAPI()

# Разрешаем запросы с любого сайта
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
    genai.configure(api_key=GEMINI_API_KEY)
    # ИСПОЛЬЗУЕМ СТАБИЛЬНУЮ ВЕРСИЮ 1.5
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    print("ВНИМАНИЕ: Ключ GEMINI_API_KEY не найден в Environment Variables!")

class ChatRequest(BaseModel):
    text: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not GEMINI_API_KEY:
        return {"reply": "Ошибка сервера: API ключ не добавлен в настройки Render (Environment)."}
        
    try:
        prompt = f"Ты изящный и умный ИИ-репетитор по информатике (ОГЭ). Отвечай кратко, дружелюбно, используй эмодзи по минимуму.\n\nВопрос ученика: {req.text}"
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        print(f"Детальная ошибка: {str(e)}")
        return {"reply": f"Произошла ошибка на сервере при обращении к ИИ. Проверь логи (Logs) на Render."}
