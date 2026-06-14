"""Unit tests for the deterministic diagnosis matcher."""

from __future__ import annotations

from app.rules.diagnosis_matcher import match_diagnosis
from tests.helpers import claim_request


def test_diabetes_maps_to_waiting_condition(policy):
    match = match_diagnosis(claim_request("TC005"), {}, policy)
    assert match.waiting_condition == "diabetes"
    assert match.excluded_condition is None


def test_obesity_maps_to_exclusion(policy):
    match = match_diagnosis(claim_request("TC012"), {}, policy)
    assert match.excluded_condition is not None
    lowered = match.excluded_condition.lower()
    assert "obesity" in lowered or "bariatric" in lowered


def test_plain_diagnosis_maps_to_nothing(policy):
    match = match_diagnosis(claim_request("TC004"), {}, policy)  # "Viral Fever"
    assert match.waiting_condition is None
    assert match.excluded_condition is None
