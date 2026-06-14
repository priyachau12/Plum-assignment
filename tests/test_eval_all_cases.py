"""Full eval: run all 12 provided test cases through POST /claims and assert
each matches its expected outcome. This is the automated version of the eval
report (see scripts/run_eval.py for the human-readable report)."""

from __future__ import annotations

from tests.helpers import case_input


def _decide(client, case_id: str) -> dict:
    return client.post("/claims", json=case_input(case_id)).json()


def test_tc001_wrong_document_blocked(client):
    b = _decide(client, "TC001")
    assert b["status"] == "BLOCKED" and b["decision"] is None
    assert any(i["reason"] == "MISSING_REQUIRED_DOCUMENT" for i in b["blocking_issues"])


def test_tc002_unreadable_blocked(client):
    b = _decide(client, "TC002")
    assert b["status"] == "BLOCKED"
    assert any(i["reason"] == "UNREADABLE_DOCUMENT" for i in b["blocking_issues"])


def test_tc003_patient_mismatch_blocked(client):
    b = _decide(client, "TC003")
    assert b["status"] == "BLOCKED"
    assert any(i["reason"] == "PATIENT_MISMATCH" for i in b["blocking_issues"])


def test_tc004_clean_approval(client):
    b = _decide(client, "TC004")
    assert b["decision"] == "APPROVED"
    assert b["approved_amount"] == 1350
    assert b["confidence"] > 0.85


def test_tc005_waiting_period_diabetes(client):
    b = _decide(client, "TC005")
    assert b["decision"] == "REJECTED"
    assert "WAITING_PERIOD" in b["rejection_reasons"]
    # must state the eligibility date
    assert "2024-11-30" in (b["note"] or "")


def test_tc006_dental_partial(client):
    b = _decide(client, "TC006")
    assert b["decision"] == "PARTIAL"
    assert b["approved_amount"] == 8000
    covered = {li["description"]: li["covered"] for li in b["line_items"]}
    assert covered["Root Canal Treatment"] is True
    assert covered["Teeth Whitening"] is False


def test_tc007_mri_pre_auth_missing(client):
    b = _decide(client, "TC007")
    assert b["decision"] == "REJECTED"
    assert "PRE_AUTH_MISSING" in b["rejection_reasons"]


def test_tc008_per_claim_exceeded(client):
    b = _decide(client, "TC008")
    assert b["decision"] == "REJECTED"
    assert "PER_CLAIM_EXCEEDED" in b["rejection_reasons"]
    assert "5000" in (b["note"] or "")


def test_tc009_same_day_fraud_manual_review(client):
    b = _decide(client, "TC009")
    assert b["decision"] == "MANUAL_REVIEW"
    assert "SAME_DAY_CLAIMS" in (b["note"] or "")


def test_tc010_network_discount_before_copay(client):
    b = _decide(client, "TC010")
    assert b["decision"] == "APPROVED"
    assert b["approved_amount"] == 3240
    fb = b["financial_breakdown"]
    assert fb["after_network_discount"] == 3600  # 20% discount FIRST
    assert fb["after_copay"] == 3240  # then 10% co-pay


def test_tc011_component_failure_degraded_but_approved(client):
    b = _decide(client, "TC011")
    assert b["decision"] == "APPROVED"
    assert b["degraded"] is True
    assert b["confidence"] < 0.85  # lower than a normal full-pipeline approval
    assert "manual review" in (b["note"] or "").lower()
    assert any(t["status"] == "FAILED" for t in b["trace"])


def test_tc012_excluded_condition(client):
    b = _decide(client, "TC012")
    assert b["decision"] == "REJECTED"
    assert "EXCLUDED_CONDITION" in b["rejection_reasons"]
    assert b["confidence"] > 0.90
