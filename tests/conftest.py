"""Shared pytest fixtures.

`client` wraps the app in a `TestClient` used as a CONTEXT MANAGER, which is
what triggers FastAPI's lifespan (startup/shutdown). Without the `with`, the
policy/graph would never be loaded onto `app.state`.

`policy` loads the real provided policy for testing pure logic without HTTP.

`_disable_llm` (autouse) forces the deterministic, offline path: no LLM calls
during the test suite. The LLM-handling code is exercised separately with a fake
client in `test_llm_nodes.py`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.policy.policy_loader import load_policy


@pytest.fixture(autouse=True)
def _disable_llm(monkeypatch):
    monkeypatch.setenv("USE_LLM", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:  # `with` => lifespan runs
        yield test_client


@pytest.fixture
def policy():
    return load_policy(get_settings().policy_file_path)
