from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _first_env(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


OPENAI_API_KEY = _first_env("OPENAI_API_KEY", "LLM_API_KEY", "CURSOR_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o").strip() or "gpt-4o"
CURSOR_MODEL = os.getenv("CURSOR_MODEL", "composer-2.5").strip() or "composer-2.5"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None


def key_kind(api_key: str | None = None) -> str:
    key = (api_key or OPENAI_API_KEY or "").strip()
    if key.startswith("crsr_"):
        return "cursor"
    if key.startswith("sk-or-"):
        return "openrouter"
    if key:
        return "openai"
    return "none"


def is_cursor_dashboard_key(api_key: str | None = None) -> bool:
    return key_kind(api_key) == "cursor"
