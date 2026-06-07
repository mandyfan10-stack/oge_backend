"""Centralised user-facing reply strings (Russian).

The frontend (`chatClient.extractErrorMessage`) looks for the `reply` key
first, so every error response must carry one of these. Keeping them in a
single module avoids the previous drift where the same text lived in both
server.py and routes/chat.py.
"""

SERVICE_UNAVAILABLE_REPLY = "Ошибка сервера: Сервис временно недоступен."
RATE_LIMIT_REPLY = (
    "Упс! Кажется, нейросеть сейчас немного перегружена запросами ⏳ "
    "Пожалуйста, подожди несколько секунд и попробуй снова!"
)
TIMEOUT_REPLY = "Превышено время ожидания ответа от ИИ. Пожалуйста, попробуй позже."
GENERIC_ERROR_REPLY = (
    "Произошла ошибка на сервере при обращении к ИИ. Пожалуйста, попробуй позже."
)

# HTTP status → user-facing reply for auth failures. FastAPI's default
# {"detail": ...} would not be parsed by the frontend.
AUTH_REPLY_MAP = {
    401: "Сессия Telegram отсутствует. Перезапустите мини-приложение через бота.",
    403: "Подпись Telegram недействительна или истекла. Перезапустите мини-приложение.",
}
