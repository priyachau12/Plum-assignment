"""Tests for app.config.Settings."""

from __future__ import annotations

from app.config import Settings, get_settings


def test_defaults_are_sane():
    s = Settings()
    assert s.app_name
    assert s.environment == "development"
    # Default policy path points at the provided file at the repo root.
    assert s.policy_file_path.name == "policy_terms.json"


def test_extraction_agent_defaults():
    # _env_file=None so this asserts the CODE defaults, not whatever a local .env
    # happens to set.
    s = Settings(_env_file=None)
    assert s.extraction_agent_enabled is True
    assert s.extraction_confidence_threshold == 0.67
    assert s.extraction_max_attempts == 3
    assert s.llm_model_fast  # a cheap baseline model is configured
    # The strong/escalation tier is the existing llm_model.
    assert s.llm_model and s.llm_model != s.llm_model_fast


def test_extraction_agent_env_override(monkeypatch):
    monkeypatch.setenv("EXTRACTION_AGENT_ENABLED", "false")
    monkeypatch.setenv("EXTRACTION_MAX_ATTEMPTS", "1")
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.extraction_agent_enabled is False
        assert s.extraction_max_attempts == 1
    finally:
        get_settings.cache_clear()


def test_env_override(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    get_settings.cache_clear()  # drop the cached singleton so env is re-read
    try:
        assert get_settings().log_level == "DEBUG"
    finally:
        get_settings.cache_clear()  # don't leak the override into other tests
