"""Tests for the deterministic document checks (TC001–TC003 + a clean case)."""

from __future__ import annotations

from app.models.decision import BlockingReason
from app.verification.document_checks import run_document_checks
from tests.helpers import claim_request


def test_tc001_missing_required_document_names_both_types(policy):
    result = run_document_checks(claim_request("TC001"), policy)
    assert not result.passed
    issue = next(
        i for i in result.blocking_issues if i.reason == BlockingReason.MISSING_REQUIRED_DOCUMENT
    )
    # The message must name what was uploaded AND what is required (not generic).
    assert "PRESCRIPTION" in issue.message
    assert "HOSPITAL_BILL" in issue.message
    assert "HOSPITAL_BILL" in issue.details["missing"]


def test_tc002_unreadable_document_asks_for_reupload_without_rejecting(policy):
    result = run_document_checks(claim_request("TC002"), policy)
    assert not result.passed
    issue = next(
        i for i in result.blocking_issues if i.reason == BlockingReason.UNREADABLE_DOCUMENT
    )
    assert "PHARMACY_BILL" in issue.message
    assert "re-upload" in issue.message.lower()
    assert "not been rejected" in issue.message.lower()


def test_tc003_patient_mismatch_names_both_patients(policy):
    result = run_document_checks(claim_request("TC003"), policy)
    assert not result.passed
    issue = next(i for i in result.blocking_issues if i.reason == BlockingReason.PATIENT_MISMATCH)
    assert "Rajesh Kumar" in issue.message
    assert "Arjun Mehta" in issue.message


def test_tc004_clean_claim_passes_but_still_traces_every_check(policy):
    result = run_document_checks(claim_request("TC004"), policy)
    assert result.passed
    assert result.blocking_issues == []
    steps = {entry.step for entry in result.trace_entries}
    assert steps == {
        "check.required_documents",
        "check.readability",
        "check.same_patient",
    }
