from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, set_key

from models import ApiConfig
from storage.json_store import JsonStore
from utils.paths import ENV_PATH, SETTINGS_PATH


class SettingsManager:
    def __init__(self, settings_path: Path = SETTINGS_PATH, env_path: Path = ENV_PATH) -> None:
        self._store = JsonStore(settings_path, {})
        self.env_path = env_path

    def get(self, key: str, default: Any = None) -> Any:
        data = self._store.read()
        return data.get(key, default) if isinstance(data, dict) else default

    def set(self, key: str, value: Any) -> None:
        data = self._store.read()
        if not isinstance(data, dict):
            data = {}
        data[key] = value
        self._store.write(data)

    def load_api_config(self) -> ApiConfig:
        env = {**dotenv_values(self.env_path), **os.environ}
        return ApiConfig(
            api_key=str(env.get("API_KEY") or ""),
            base_url=str(env.get("API_BASE_URL") or "https://api.openai.com/v1"),
            prompt_endpoint=str(env.get("PROMPT_ENDPOINT") or "/responses"),
            image_endpoint=str(env.get("IMAGE_ENDPOINT") or "/images/generations"),
            image_edit_endpoint=str(env.get("IMAGE_EDIT_ENDPOINT") or "/images/edits"),
            auth_header=str(env.get("API_AUTH_HEADER") or "Authorization"),
            auth_prefix=str(env.get("API_AUTH_PREFIX") or "Bearer"),
            timeout_seconds=int(env.get("API_TIMEOUT_SECONDS") or 180),
            max_retries=max(0, int(env.get("API_MAX_RETRIES") or 2)),
            retry_backoff_seconds=max(0.0, float(env.get("API_RETRY_BACKOFF_SECONDS") or 2)),
        )

    def save_api_key(self, api_key: str) -> None:
        self.env_path.touch(exist_ok=True)
        set_key(str(self.env_path), "API_KEY", api_key, quote_mode="never")
