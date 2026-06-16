"""Tests for app.config.Settings."""

from __future__ import annotations

from app.config import Settings, get_settings


def test_defaults_are_sane():
    s = Settings()
    assert s.app_name
    assert s.environment == "development"
    # Default policy path points at the provided file at the repo root.
    assert s.policy_file_path.name == "policy_terms.json"


def test_env_override(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    get_settings.cache_clear()  # drop the cached singleton so env is re-read
    try:
        assert get_settings().log_level == "DEBUG"
    finally:
        get_settings.cache_clear()  # don't leak the override into other tests
