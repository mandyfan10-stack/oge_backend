import asyncio
import logging
from typing import AsyncGenerator

from groq import AsyncGroq

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = (
    "Ты изящный и умный ИИ-репетитор по информатике (ОГЭ). "
    "Отвечай на русском языке кратко, дружелюбно, используй эмодзи по минимуму. "
    "Твоя цель — помочь ученику САМОМУ прийти к ответу через наводящие вопросы и объяснение теории. "
    "Не давай ответ напрямую."
)

TIMEOUT_REPLY = "Превышено время ожидания ответа от ИИ. Пожалуйста, попробуй позже."
GENERIC_ERROR_REPLY = "Произошла ошибка на сервере при обращении к ИИ. Пожалуйста, попробуй позже."


def build_messages(text: str, history, task_description: str | None) -> list[dict]:
    system = BASE_SYSTEM_PROMPT
    if task_description:
        system += f"\n\nОПИСАНИЕ ЗАДАНИЯ:\n{task_description}"
    messages = [{"role": "system", "content": system}]
    if history:
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": f"Вопрос ученика: {text}"})
    return messages


async def stream_groq(
    client: AsyncGroq, messages: list[dict], request_id: str
) -> AsyncGenerator[str, None]:
    stream = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
        stream=True,
    )

    try:
        async def _inner():
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

        gen = _inner()
        while True:
            try:
                content = await asyncio.wait_for(gen.__anext__(), timeout=30.0)
                yield content
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                logger.warning("[%s] Таймаут стриминга Groq", request_id)
                yield f"\n\n[{TIMEOUT_REPLY}]"
                break
    except asyncio.CancelledError:
        logger.info("[%s] Клиент отключился во время стриминга.", request_id)
        raise
    except Exception:
        logger.exception("[%s] Ошибка стриминга Groq", request_id)
        yield f" [Ошибка: {GENERIC_ERROR_REPLY}]"
    finally:
        try:
            await stream.close()
        except Exception:
            pass
