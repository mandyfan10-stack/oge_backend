import os
from fastapi.testclient import TestClient

# Must set fake API key before importing create_groq_client so we can mock correctly
os.environ["GROQ_API_KEY"] = "fake-key"

import server
from server import app, create_groq_client

client = TestClient(app)

def test_rate_limiting():
    # Setup mock client
    server.client = create_groq_client()

    class MockChoices:
        def __init__(self):
            class MockMessage:
                content = "hello"
            self.message = MockMessage()

    class MockResponse:
        choices = [MockChoices()]

    async def mock_create(*args, **kwargs):
        return MockResponse()

    server.client.chat.completions.create = mock_create

    # Test limit is 10
    # First clear out states just in case
    server.request_counts.clear()

    for _ in range(10):
        resp = client.post("/api/chat", json={"text": "hello"})
        assert resp.status_code == 200

    # 11th request should be rate limited
    resp = client.post("/api/chat", json={"text": "hello"})
    assert resp.status_code == 200
    assert resp.json().get("reply") == server.RATE_LIMIT_REPLY
