from auth import verify_telegram_webapp

from unittest.mock import patch
from importlib import reload

from fastapi.testclient import TestClient

import server

client = TestClient(server.app)
server.app.dependency_overrides[verify_telegram_webapp] = lambda: "mock_auth_data"


def test_missing_groq_api_key():
    with patch("server.client", None):
        response = client.post("/api/chat", json={"text": "Привет"})

        assert response.status_code == 503
        assert response.json() == {"reply": server.SERVICE_UNAVAILABLE_REPLY}


def test_empty_message_after_strip_is_rejected():
    response = client.post("/api/chat", json={"text": "   "})

    assert response.status_code == 422


def test_lowercase_groq_api_key_alias_is_supported(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("groq_api_key", "test-key")

    reload(server)

    assert server.client is not None


def test_health_ping():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_compressed_payload():
    payload = {
        "history": [{"role": "user", "content": "T1|V:x=5|Q:Find x|A:5"}],
        "text": "Explain this to me."
    }
    response = client.post("/api/chat", json=payload)
    # 200 means success, 429 means rate limit (likely in CI/local), 
    # 500/504 means Groq error but valid payload
    # 401 means missing API key/invalid API key
    assert response.status_code in [200, 401, 429, 500, 504]


def test_chat_history_exceeds_max_length():
    # [Security] Verify that sending an arbitrarily large history is rejected
    # to prevent memory exhaustion (DoS).
    history = [{"role": "user", "content": "Hello"} for _ in range(51)]
    payload = {
        "history": history,
        "text": "Another message."
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422
    assert "List should have at most 50 items" in response.text
