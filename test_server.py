import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

import server

client = TestClient(server.app)

def test_missing_groq_api_key():
    # Patch the global client to None
    with patch("server.client", None):
        response = client.post(
            "/api/chat",
            json={"text": "Привет"}
        )

        assert response.status_code == 200
        assert response.json() == {
            "reply": "Ошибка сервера: Сервис временно недоступен."
        }
