"""Unit tests for the deterministic decision rules, isolated from the pipeline."""

from __future__ import annotations

from app.models.decision import Decision, DiagnosisMatch, RejectionReason
from app.rules.bill_details import gather_bill_details
from app.rules.decision_rules import apply_rules
from app.rules.diagnosis_matcher import match_diagnosis
from tests.helpers import claim_request


def _decide(case_id: str, policy, degraded: bool = False):
    request = claim_request(case_id)
    member = policy.get_member(request.member_id)
    diagnosis = match_diagnosis(request, {}, policy)
    bill = gather_bill_details(request, policy, {})
    return apply_rules(request, member, diagnosis, policy, bill, {}, degraded)


def test_copay_only_no_network(policy):
    r = _decide("TC004", policy)
    assert r.decision is Decision.APPROVED
    assert r.approved_amount == 1350
    assert r.financial_breakdown["is_network"] is False


def test_network_discount_applied_before_copay(policy):
    r = _decide("TC010", policy)
    assert r.decision is Decision.APPROVED
    assert r.financial_breakdown["after_network_discount"] == 3600
    assert r.financial_breakdown["after_copay"] == 3240
    assert r.approved_amount == 3240


def test_per_claim_limit_rejects(policy):
    r = _decide("TC008", policy)
    assert r.decision is Decision.REJECTED
    assert RejectionReason.PER_CLAIM_EXCEEDED in r.rejection_reasons


def test_exclusion_takes_precedence_over_waiting_and_limit(policy):
    # TC012 obesity is both an exclusion and (obesity_treatment) a waiting cond;
    # exclusion must win and the amount (8000>5000) must NOT drive the reason.
    r = _decide("TC012", policy)
    assert r.decision is Decision.REJECTED
    assert RejectionReason.EXCLUDED_CONDITION in r.rejection_reasons
    assert r.confidence > 0.90


def test_degraded_lowers_confidence(policy):
    normal = _decide("TC011", policy, degraded=False)
    degraded = _decide("TC011", policy, degraded=True)
    assert degraded.confidence < normal.confidence
    assert degraded.decision is Decision.APPROVED


def test_unknown_member_not_eligible(policy):
    request = claim_request("TC004")
    bill = gather_bill_details(request, policy, {})
    r = apply_rules(request, None, DiagnosisMatch(), policy, bill, {}, False)
    assert r.decision is Decision.REJECTED
    assert RejectionReason.NOT_ELIGIBLE in r.rejection_reasons
