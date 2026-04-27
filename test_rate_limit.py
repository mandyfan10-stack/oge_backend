from fastapi.testclient import TestClient
import server


def test_rate_limit_enforced():
    # Reset state
    server.request_counts.clear()
    client = TestClient(server.app)

    # 10 requests within the limit should succeed
    for _ in range(10):
        response = client.post("/api/chat", json={"text": "Привет"})
        assert response.json() != {"reply": server.RATE_LIMIT_REPLY}

    # The 11th request should be rate-limited
    response = client.post("/api/chat", json={"text": "Привет"})
    assert response.json() == {"reply": server.RATE_LIMIT_REPLY}


def test_rate_limit_window_expiration():
    # Reset state
    server.request_counts.clear()
    client = TestClient(server.app)

    # Fill up the limit
    for _ in range(10):
        response = client.post("/api/chat", json={"text": "Привет"})
        assert response.json() != {"reply": server.RATE_LIMIT_REPLY}

    # Next one is limited
    response = client.post("/api/chat", json={"text": "Привет"})
    assert response.json() == {"reply": server.RATE_LIMIT_REPLY}

    # Manually shift timestamps backward by 61 seconds
    ip = "testclient"  # FastAPI test client IP defaults to testclient
    if ip in server.request_counts:
        server.request_counts[ip] = [ts - 61 for ts in server.request_counts[ip]]

    # Request should succeed now
    response = client.post("/api/chat", json={"text": "Привет"})
    assert response.json() != {"reply": server.RATE_LIMIT_REPLY}
