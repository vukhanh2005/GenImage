from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


ROOT_DIR = project_root()
TEMP_DIR = ROOT_DIR / "temp"
LOG_DIR = ROOT_DIR / "logs"
ENV_PATH = ROOT_DIR / ".env"
HISTORY_PATH = ROOT_DIR / "history.json"
SETTINGS_PATH = ROOT_DIR / "settings.json"


def ensure_app_directories() -> None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

