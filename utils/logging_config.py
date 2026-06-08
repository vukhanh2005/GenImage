from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from utils.paths import LOG_DIR, ensure_app_directories


SENSITIVE_KEYS = {"api_key", "authorization", "x-api-key", "token"}


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: mask_secret(str(item)) if key.lower() in SENSITIVE_KEYS else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        return f"{value[:240]}...<{len(value)} chars>...{value[-80:]}"
    return value


def configure_logging() -> None:
    ensure_app_directories()
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

