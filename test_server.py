from unittest.mock import patch
from importlib import reload

from fastapi.testclient import TestClient

import server

client = TestClient(server.app)


def test_missing_groq_api_key():
    with patch("server.client", None):
        response = client.post("/api/chat", json={"text": "Привет"})

        assert response.status_code == 200
        assert response.json() == {"reply": server.SERVICE_UNAVAILABLE_REPLY}


def test_empty_message_after_strip_is_rejected():
    response = client.post("/api/chat", json={"text": "   "})

    assert response.status_code == 422


def test_lowercase_groq_api_key_alias_is_supported(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("groq_api_key", "test-key")

    reload(server)

    assert server.client is not None


def test_history_exceeds_max_length_is_rejected():
    history = [{"role": "user", "content": "hello"}] * 51
    response = client.post("/api/chat", json={"text": "hi", "history": history})

    assert response.status_code == 422
