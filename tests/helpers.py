"""Test helpers: load scenarios straight from the provided `test_cases.json`.

Building `ClaimRequest` objects from the real test data ties our tests to the
exact inputs the system is graded on. `test_cases.json` is a read-only base
file; we only read it.
"""

from __future__ import annotations

import json

from app.config import get_settings
from app.models.claim import ClaimRequest


def _load() -> dict[str, dict]:
    path = get_settings().policy_file_path.parent / "test_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))["test_cases"]
    return {case["case_id"]: case for case in cases}


TEST_CASES = _load()


def case_input(case_id: str) -> dict:
    """Raw `input` block for a case (as submitted to the API)."""
    return TEST_CASES[case_id]["input"]


def claim_request(case_id: str) -> ClaimRequest:
    """A parsed `ClaimRequest` for a case."""
    return ClaimRequest(**case_input(case_id))
