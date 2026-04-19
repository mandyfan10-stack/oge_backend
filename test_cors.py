import os
import pytest
from fastapi.testclient import TestClient
from importlib import reload
import server

def test_cors_allowed_origin():
    # Set ALLOWED_ORIGINS to a specific domain
    os.environ["ALLOWED_ORIGINS"] = "https://example.com"

    # Reload server module to pick up the new env var
    reload(server)
    client = TestClient(server.app)

    response = client.options(
        "/api/chat",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"

def test_cors_disallowed_origin():
    # Set ALLOWED_ORIGINS to a specific domain
    os.environ["ALLOWED_ORIGINS"] = "https://example.com"

    # Reload server module to pick up the new env var
    reload(server)
    client = TestClient(server.app)

    response = client.options(
        "/api/chat",
        headers={
            "Origin": "https://malicious.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    # In FastAPI/Starlette CORS middleware, if origin is not allowed,
    # it might still return 200 but without the Access-Control-Allow-Origin header
    assert response.headers.get("Access-Control-Allow-Origin") is None

def test_cors_multiple_origins():
    # Set ALLOWED_ORIGINS to multiple domains
    os.environ["ALLOWED_ORIGINS"] = "https://example.com, https://another.com"

    # Reload server module to pick up the new env var
    reload(server)
    client = TestClient(server.app)

    # Test first domain
    response1 = client.options(
        "/api/chat",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response1.headers.get("Access-Control-Allow-Origin") == "https://example.com"

    # Test second domain
    response2 = client.options(
        "/api/chat",
        headers={
            "Origin": "https://another.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response2.headers.get("Access-Control-Allow-Origin") == "https://another.com"

def test_cors_no_allowed_origins():
    # Set ALLOWED_ORIGINS to empty
    os.environ["ALLOWED_ORIGINS"] = ""

    # Reload server module to pick up the new env var
    reload(server)
    client = TestClient(server.app)

    response = client.options(
        "/api/chat",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.headers.get("Access-Control-Allow-Origin") is None
