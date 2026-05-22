from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="User's chat message")
    history: Optional[list[ChatMessage]] = Field(
        default=None, max_length=20, description="Previous messages (max 20)"
    )
    task_description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Task description from frontend (no correct answer)",
    )

    @field_validator("text", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("history", mode="before")
    @classmethod
    def drop_empty_history_items(cls, value: Any) -> Any:
        # Defensive: an old frontend may persist an empty assistant placeholder
        # (from an interrupted stream) and replay it as a history item. Silently
        # discard those so a stale localStorage doesn't poison the whole request.
        if not value or not isinstance(value, list):
            return value
        cleaned = []
        for item in value:
            if isinstance(item, dict):
                content = item.get("content")
                if isinstance(content, str) and content.strip():
                    cleaned.append(item)
            else:
                cleaned.append(item)
        return cleaned
