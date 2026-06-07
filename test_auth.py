"""
Tests for Telegram WebApp authentication (auth.py).
These cover cases that were previously untested:
  - valid init_data passes
  - missing hash is rejected
  - expired auth_date (replay attack) is rejected
  - missing bot token fails closed
"""

import hmac
import hashlib
import time
from urllib.parse import urlencode


def _make_init_data(bot_token: str, extra: dict | None = None, age_seconds: int = 0) -> str:
    """Helper: build a valid signed Telegram initData string."""
    params = {
        "auth_date": str(int(time.time()) - age_seconds),
        "user": '{"id":123456,"first_name":"Test"}',
    }
    if extra:
        params.update(extra)

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    signature = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    params["hash"] = signature
    return urlencode(params)


BOT_TOKEN = "test-bot-token-12345"


def test_valid_init_data_passes(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    import importlib
    import auth
    importlib.reload(auth)

    init_data = _make_init_data(BOT_TOKEN)
    assert auth.validate_telegram_init_data(init_data) is True


def test_wrong_hash_is_rejected(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    import importlib
    import auth
    importlib.reload(auth)

    init_data = _make_init_data(BOT_TOKEN)
    tampered = init_data.replace(init_data.split("hash=")[1][:8], "deadbeef")
    assert auth.validate_telegram_init_data(tampered) is False


def test_missing_hash_is_rejected(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    import importlib
    import auth
    importlib.reload(auth)

    init_data = f"auth_date={int(time.time())}&user=test"
    assert auth.validate_telegram_init_data(init_data) is False


def test_expired_auth_date_is_rejected(monkeypatch):
    """Auth tokens older than 24 h must be rejected (replay attack prevention)."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    import importlib
    import auth
    importlib.reload(auth)

    old_init_data = _make_init_data(BOT_TOKEN, age_seconds=25 * 3600)
    assert auth.validate_telegram_init_data(old_init_data) is False


def test_missing_bot_token_fails_closed(monkeypatch):
    """If TELEGRAM_BOT_TOKEN is not set, every request must be denied."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    import importlib
    import auth
    importlib.reload(auth)

    init_data = _make_init_data(BOT_TOKEN)
    assert auth.validate_telegram_init_data(init_data) is False


def test_malformed_auth_date_is_rejected(monkeypatch):
    """A non-numeric auth_date must be rejected, not crash with a 500."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    import importlib
    import auth
    importlib.reload(auth)

    init_data = "auth_date=not-a-number&user=test&hash=deadbeef"
    assert auth.validate_telegram_init_data(init_data) is False
