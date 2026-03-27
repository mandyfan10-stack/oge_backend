from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os

app = FastAPI()

# 1. Настройка CORS (Разрешаем твоему сайту на GitHub отправлять сюда запросы)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для безопасности потом замени "*" на "https://твой-ник.github.io"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. БЕЗОПАСНАЯ ИНТЕГРАЦИЯ КЛЮЧА
# В идеале ключ берется из скрытого файла окружения (os.getenv).
# НИКОГДА НЕ ЗАГРУЖАЙ ЭТОТ ФАЙЛ НА GITHUB!
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "ВСТАВЬ_СЮДА_СВОЙ_НОВЫЙ_КЛЮЧ")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Формат получаемых данных от твоего сайта
class ChatRequest(BaseModel):
    text: str

# 3. Единственный маршрут (эндпоинт), к которому обращается сайт
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        # Инструкция для нейросети + сам вопрос пользователя
        prompt = f"Ты изящный и умный ИИ-репетитор по информатике (ОГЭ). Отвечай кратко, дружелюбно, используй эмодзи по минимуму.\n\nВопрос ученика: {req.text}"
        
        response = model.generate_content(prompt)
        return {"reply": response.text}
    except Exception as e:
        print("Ошибка:", e)
        return {"reply": "Произошла ошибка на сервере при обращении к ИИ."}

# Запуск сервера (если запускать файл напрямую)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
