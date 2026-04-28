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


def test_rate_limiting_returns_429():
    class DummyChoice:
        class DummyMessage:
            content = "hi"
        message = DummyMessage()

    class DummyResponse:
        choices = [DummyChoice()]

    class DummyCreate:
        async def create(self, **kwargs):
            return DummyResponse()

    class DummyCompletions:
        create = DummyCreate().create

    class DummyChat:
        completions = DummyCompletions()

    class DummyClient:
        chat = DummyChat()

    with patch("server.client", new=DummyClient()):
        # Clear rate limits before the test
        server.ip_request_counts.clear()

        # Do N successful requests up to the max limit
        for i in range(server.RATE_LIMIT_MAX_REQUESTS):
            response = client.post("/api/chat", json={"text": "Привет"})
            assert response.status_code != 429

        # The next request should be rate limited
        response_429 = client.post("/api/chat", json={"text": "Привет"})
        assert response_429.status_code == 429
        assert response_429.json() == {"reply": server.RATE_LIMIT_REPLY}
