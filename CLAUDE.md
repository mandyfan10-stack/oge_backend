# CLAUDE.md — oge_backend-main

FastAPI-бэкенд для Telegram WebApp `oge-bot`. Обслуживает чат с ИИ-репетитором по информатике ОГЭ через Groq llama-3.3-70b.

## Что делает

- `POST /api/chat` — стримит ответ от Groq как `text/plain` (плоский поток токенов, не SSE).
- `GET  /api/health` — статус приложения и наличие ключей.

## Архитектура

```
server.py                 — FastAPI app factory, lifespan, CORS, security-headers, rate-limit handler
state.py                  — синглтон AsyncGroq client (инициализируется в lifespan)
routes/chat.py            — POST /api/chat, лимит 6/мин на IP (slowapi)
routes/health.py          — GET /api/health
schemas.py                — Pydantic-модели ChatRequest / ChatMessage
services/groq_service.py  — build_messages() + stream_groq() с per-chunk timeout 30s
auth.py                   — verify_telegram_webapp() (HMAC-SHA256 проверка initData, TTL 24ч)
```

## Контракт запроса `/api/chat`

```json
{
  "text": "string, 1..2000 символов (после strip)",
  "history": [{"role": "user|assistant", "content": "1..2000"}, ...],
  "task_description": "string, max 500"
}
```

`history` и `task_description` — optional. `history` обрезан до 20 элементов.

Header: `X-Telegram-Init-Data: <Telegram WebApp initData>` (обязателен).

### Частые причины HTTP 422

- `text` пустой или только пробелы (после `.strip()`).
- `history[].role === "system"` — система-роль запрещена паттерном `^(user|assistant)$` (защита от prompt injection).
- `history` длиннее 20 элементов.
- `task_description` длиннее 500 символов.

`history` элементы с пустым `content` **молча отбрасываются** валидатором `drop_empty_history_items` (см. [schemas.py](schemas.py)) — это страховка от устаревших клиентов, у которых в localStorage остался placeholder ассистента от прерванного стрима. Старый ChatMessage-валидатор с `min_length=1` оставлен как hard guard.

## Контракт ответа

- Успех: `200` + поток токенов (`media_type=text/plain`). Стрим может содержать в конце inline-сообщение об ошибке вида `[Ошибка: ...]` (когда Groq падает в середине стрима).
- Ошибки имеют форму `{"reply": "<рус. текст для пользователя>", "detail": "<техн. деталь>"}`. Фронт первым делом ищет ключ `reply` в JSON-ответе.
  - `401/403` — невалидный/отсутствующий Telegram initData.
  - `422` — Pydantic-валидация.
  - `429` — превышен rate limit (6/мин).
  - `503` — Groq недоступен или нет `GROQ_API_KEY`.
  - `504` — таймаут Groq API.

## ENV-переменные

| Переменная | Назначение | Notes |
|---|---|---|
| `GROQ_API_KEY` | ключ Groq | принимает также `groq_api_key` (lowercase alias) |
| `TELEGRAM_BOT_TOKEN` | bot token для HMAC-проверки initData | без него auth fails closed (все запросы 401/403) |
| `ALLOWED_ORIGINS` | CSV-список разрешённых Origin | принимает `allowed_origins` alias; по умолчанию `https://mandyfan10-stack.github.io` + localhost |

`.env.example` — шаблон.

## Запуск

```bash
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

Python 3.11.10 (см. `.python-version`).

## Тесты

```bash
pytest -x
```

Существующие наборы:
- `test_server.py` — `/api/chat` валидация, дроп пустых history-элементов, health, lifespan, lowercase env alias.
- `test_auth.py` — HMAC проверка Telegram initData (replay, missing-token, wrong-hash).
- `test_cors.py` — динамический список Origin (по env-переменной и дефолту).
- `test_security_headers.py` — CSP / XFO / HSTS присутствуют.

В тестах `verify_telegram_webapp` подменяется через `app.dependency_overrides`.

## Деплой

`render.yaml` → Render.com (free plan). Health-check `/api/health`. autoDeploy при push в `main`. Docker-вариант есть в `Dockerfile` (python:3.11-slim).

## Конвенции / подводные камни

- Все user-facing сообщения **на русском**. Структура `{"reply": "..."}` обязательна — фронт первым делом ищет ключ `reply` в JSON-ответе.
- Никогда не добавлять `role: "system"` в `history` со стороны клиента — system-промпт собирает сам бэкенд (`services/groq_service.py: BASE_SYSTEM_PROMPT`).
- `task_description` инжектится в system-промпт → перед расширением лимита 500 символов оценить prompt-injection-риск.
- Groq-клиент с `timeout=10s`; стрим оборачивает каждый чанк в `asyncio.wait_for(..., 30s)`.
- Логи — stdout, простой формат `LEVEL: message` (видны в Render dashboard).
- `state.groq_client` инициализируется в lifespan, а не на module-level — иначе тесты падают при отсутствии env-ключа.
