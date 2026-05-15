import os
import time
import hmac
import hashlib
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException, status
import logging

logger = logging.getLogger(__name__)

# The Telegram Bot Token must be securely stored in environment variables.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def validate_telegram_init_data(init_data: str) -> bool:
    """
    Cryptographically verifies the authenticity of the Telegram WebApp initData.
    Prevents unauthorized API calls and replay attacks.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is missing! Failing closed.")
        return False

    try:
        # Parse the URL-encoded initData
        parsed_data = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return False

    if "hash" not in parsed_data:
        return False

    received_hash = parsed_data.pop("hash")

    # [Security] Prevent Replay Attacks: Enforce token expiration (e.g., 24 hours)
    auth_date = int(parsed_data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        logger.warning("Telegram auth_date expired. Potential replay attack.")
        return False

    # 1. Sort the key-value pairs alphabetically by key
    # 2. Join them with a newline character
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed_data.items())
    )

    # 3. Compute the secret key: HMAC-SHA256(key="WebAppData", msg=TELEGRAM_BOT_TOKEN)
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=TELEGRAM_BOT_TOKEN.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()

    # 4. Compute the expected hash: HMAC-SHA256(key=secret_key, msg=data_check_string)
    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    # [Security] Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(calculated_hash, received_hash)


async def verify_telegram_webapp(
    x_telegram_init_data: str = Header(None, alias="X-Telegram-Init-Data")
):
    """
    FastAPI Dependency to enforce Telegram WebApp authentication.
    """
    if not x_telegram_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authentication Header",
        )

    if not validate_telegram_init_data(x_telegram_init_data):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or Expired Telegram Authentication Data",
        )

    return x_telegram_init_data
