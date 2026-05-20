"""Shared mutable application state (Groq client singleton)."""
from typing import Optional
from groq import AsyncGroq

groq_client: Optional[AsyncGroq] = None
