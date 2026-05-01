import time
from unittest.mock import patch
from fastapi.testclient import TestClient

import server

client = TestClient(server.app)


def test_rate_limiting():
    # Clear tracking
    server._ip_tracking.clear()

    with patch("server.client", True):  # Bypass the 'if not client' check
        with patch.object(server, 'client'):
            # Send requests up to limit
            for _ in range(server.RATE_LIMIT_MAX_REQUESTS):
                response = client.post("/api/chat", json={"text": "Hello"})
                assert response.json() != {"reply": server.RATE_LIMIT_REPLY}

            # Next request should be rate limited
            response = client.post("/api/chat", json={"text": "Hello"})
            assert response.json() == {"reply": server.RATE_LIMIT_REPLY}


def test_rate_limit_different_ips():
    server._ip_tracking.clear()

    with patch("server.client", True):
        with patch.object(server, 'client'):
            for _ in range(server.RATE_LIMIT_MAX_REQUESTS):
                response = client.post("/api/chat", json={"text": "Hello"})
                assert response.json() != {"reply": server.RATE_LIMIT_REPLY}

            response = client.post("/api/chat", json={"text": "Hello"})
            assert response.json() == {"reply": server.RATE_LIMIT_REPLY}

            client2 = TestClient(server.app, client=("1.2.3.4", 50000))
            response2 = client2.post("/api/chat", json={"text": "Hello"})
            assert response2.json() != {"reply": server.RATE_LIMIT_REPLY}


def test_rate_limit_cleanup():
    server._ip_tracking.clear()

    for i in range(server.MAX_TRACKED_IPS):
        server._ip_tracking[f"ip_{i}"] = {"count": 1, "start_time": time.time()}

    assert len(server._ip_tracking) == server.MAX_TRACKED_IPS

    with patch("server.client", True):
        with patch.object(server, 'client'):
            client3 = TestClient(server.app, client=("9.9.9.9", 50000))
            response = client3.post("/api/chat", json={"text": "Hello"})

            # We bypass the groq call but might get generic error, the main thing is we hit rate limit cleanup
            # We don't get RATE_LIMIT_REPLY because it's the first request for this IP
            assert response.json() != {"reply": server.RATE_LIMIT_REPLY}
            assert len(server._ip_tracking) == 1
            assert "9.9.9.9" in server._ip_tracking
