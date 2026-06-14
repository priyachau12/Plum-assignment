"""Application configuration.

Purpose
-------
One typed, validated source of truth for every runtime setting, sourced from
environment variables (and an optional `.env`). Nothing else in the app reads
`os.environ` directly.

Why it exists
-------------
- Keeps secrets/tunables out of code (12-factor).
- Pydantic validates and coerces types at startup, so a bad value fails loudly
  and early instead of deep inside a request.

Interactions
------------
- `main.py` calls `get_settings()` during lifespan startup.
- `routes_health.py` reads settings off `app.state`.
- `loader.py` is handed `settings.policy_file_path`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the repository root from THIS file's location, not the current
# working directory. app/config.py -> app/ -> <repo root>. This makes the
# default policy path correct whether you run uvicorn from the repo root or
# run pytest from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Validated runtime settings. Field name == env var (case-insensitive)."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",  # absolute: found regardless of CWD
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated env vars rather than erroring
    )

    # --- App ---
    app_name: str = "Plum Claims Processing System"
    environment: str = "development"
    log_level: str = "INFO"

    # --- Policy ---
    # Defaults to the provided policy file at the repo root (single source of truth).
    policy_file_path: Path = PROJECT_ROOT / "policy_terms.json"

    # --- LLM ---
    use_llm: bool = True  # master switch; set false for offline/deterministic runs
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-6"  # vision-capable; configurable
    llm_timeout_seconds: float = 30.0
    anthropic_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide singleton Settings instance.

    `lru_cache` means the env is read and validated exactly once. Tests that
    want to change the environment call `get_settings.cache_clear()` first.
    """
    return Settings()
