import server
from fastapi.testclient import TestClient
from auth import verify_telegram_webapp

server.app.dependency_overrides[verify_telegram_webapp] = lambda: "mock_auth_data"

client = TestClient(server.app)

def test_chat_history_exceeds_max_length_is_rejected():
    history = [{"role": "user", "content": "hello"} for _ in range(51)]
    payload = {
        "text": "Explain this to me.",
        "history": history
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422 # Unprocessable Entity (validation error)

def test_chat_history_within_max_length_is_accepted():
    history = [{"role": "user", "content": "hello"} for _ in range(50)]
    payload = {
        "text": "Explain this to me.",
        "history": history
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code in [200, 429, 500, 504, 401, 503] # Any response meaning the payload is valid
