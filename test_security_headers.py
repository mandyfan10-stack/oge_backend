from fastapi.testclient import TestClient

import server
from auth import verify_telegram_webapp

server.app.dependency_overrides[verify_telegram_webapp] = lambda: "mock_auth_data"

client = TestClient(server.app)


def test_security_headers():
    response = client.post("/api/chat", json={"text": "hi"})

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert (
        response.headers.get("Strict-Transport-Security")
        == "max-age=31536000; includeSubDomains"
    )
    assert (
        response.headers.get("Content-Security-Policy")
        == server.SECURITY_HEADERS["Content-Security-Policy"]
    )
