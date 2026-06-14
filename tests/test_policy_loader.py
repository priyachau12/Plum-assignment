"""Tests for app.policy.policy_loader.load_policy and the policy models.

These assert against the REAL provided policy_terms.json so the loader and the
model shapes are verified against the actual file the system must apply.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.exceptions import PolicyLoadError
from app.policy.policy_loader import load_policy


def test_loads_real_policy_file():
    policy = load_policy(get_settings().policy_file_path)

    # Top-level identity
    assert policy.policy_id == "PLUM_GHI_2024"

    # Coverage numbers parsed correctly
    assert policy.coverage.per_claim_limit == 5000
    assert policy.coverage.sum_insured_per_employee == 500000

    # Category-specific optional fields parsed (diagnostic pre-auth threshold)
    diagnostic = policy.get_category("DIAGNOSTIC")
    assert diagnostic is not None
    assert diagnostic.pre_auth_threshold == 10000
    assert "MRI" in diagnostic.high_value_tests_requiring_pre_auth

    # Waiting period keys present
    assert policy.waiting_periods.specific_conditions["diabetes"] == 90

    # Roster + lookup
    assert len(policy.members) == 12
    assert policy.get_member("EMP001").name == "Rajesh Kumar"
    assert policy.get_member("NOPE") is None

    # Casing-normalized document requirement lookup
    req = policy.document_requirement("CONSULTATION")
    assert req is not None
    assert req.required == ["PRESCRIPTION", "HOSPITAL_BILL"]


def test_missing_file_raises_policy_load_error():
    with pytest.raises(PolicyLoadError):
        load_policy(Path("/definitely/not/here/policy.json"))


def test_invalid_json_raises_policy_load_error(tmp_path):
    bad = tmp_path / "broken.json"
    bad.write_text("{ this is not valid json")
    with pytest.raises(PolicyLoadError):
        load_policy(bad)


def test_schema_mismatch_raises_policy_load_error(tmp_path):
    # Valid JSON, wrong shape (missing required fields).
    bad = tmp_path / "wrong_shape.json"
    bad.write_text('{"policy_id": "X"}')
    with pytest.raises(PolicyLoadError):
        load_policy(bad)
