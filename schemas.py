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
