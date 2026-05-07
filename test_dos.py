import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)

def test_history_too_long():
    history = [{"role": "user", "content": "hello"}] * 100
    response = client.post("/api/chat", json={"text": "hello", "history": history})
    assert response.status_code == 422
