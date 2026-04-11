import hashlib
import hmac
import json
from urllib.parse import parse_qsl, unquote

from fastapi import Header, HTTPException

from .config import settings


def validate_init_data(init_data: str, bot_token: str) -> dict:
    """Валидирует initData от MAX Bridge (HMAC-SHA256)."""
    parsed = dict(parse_qsl(unquote(init_data), keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    if "user" in parsed:
        parsed["user"] = json.loads(parsed["user"])

    return parsed


async def get_current_user(x_init_data: str = Header(...)) -> dict:
    if settings.DEBUG and x_init_data == "dev":
        return {"user": {"id": 1, "first_name": "Dev", "username": "dev"}}
    return validate_init_data(x_init_data, settings.BOT_TOKEN)
