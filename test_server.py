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


def test_rate_limiting_prevents_dos(monkeypatch):
    monkeypatch.setattr(server, "RATE_LIMIT_MAX_REQUESTS", 2)
    # Clear IP tracking state
    server.ip_requests.clear()

    # Simulate client
    test_client = TestClient(server.app)

    # First request
    with patch("server.client.chat.completions.create"):
        response = test_client.post("/api/chat", json={"text": "Привет"})
    assert response.status_code == 200

    # Second request (reaches limit)
    with patch("server.client.chat.completions.create"):
        response = test_client.post("/api/chat", json={"text": "Привет 2"})
    assert response.status_code == 200

    # Third request (exceeds limit)
    response = test_client.post("/api/chat", json={"text": "Привет 3"})
    assert response.status_code == 200
    assert response.json() == {"reply": server.RATE_LIMIT_REPLY}
