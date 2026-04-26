from importlib import reload

from fastapi.testclient import TestClient

import server


def make_client(monkeypatch, allowed_origins):
    monkeypatch.setenv("ALLOWED_ORIGINS", allowed_origins)
    reload(server)
    return TestClient(server.app)


def preflight(client, origin):
    return client.options(
        "/api/chat",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )


def test_cors_allowed_origin(monkeypatch):
    client = make_client(monkeypatch, "https://example.com")
    response = preflight(client, "https://example.com")

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_disallowed_origin(monkeypatch):
    client = make_client(monkeypatch, "https://example.com")
    response = preflight(client, "https://malicious.com")

    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_cors_multiple_origins(monkeypatch):
    client = make_client(monkeypatch, "https://example.com, https://another.com")

    response1 = preflight(client, "https://example.com")
    assert response1.headers.get("Access-Control-Allow-Origin") == "https://example.com"

    response2 = preflight(client, "https://another.com")
    assert response2.headers.get("Access-Control-Allow-Origin") == "https://another.com"


def test_cors_no_allowed_origins(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("allowed_origins", raising=False)
    reload(server)
    client = TestClient(server.app)
    response = preflight(client, "https://mandyfan10-stack.github.io")

    assert (
        response.headers.get("Access-Control-Allow-Origin")
        == "https://mandyfan10-stack.github.io"
    )


def test_cors_rejects_unknown_origin_when_using_default_origins(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("allowed_origins", raising=False)
    reload(server)
    client = TestClient(server.app)
    response = preflight(client, "https://example.com")

    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_cors_empty_allowed_origins_uses_default_origins(monkeypatch):
    client = make_client(monkeypatch, "")
    response = preflight(client, "https://mandyfan10-stack.github.io")

    assert (
        response.headers.get("Access-Control-Allow-Origin")
        == "https://mandyfan10-stack.github.io"
    )


def test_lowercase_allowed_origins_alias_is_supported(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("allowed_origins", "https://example.com")
    reload(server)
    client = TestClient(server.app)

    response = preflight(client, "https://example.com")

    assert response.headers.get("Access-Control-Allow-Origin") == "https://example.com"
