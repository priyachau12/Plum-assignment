"""Unit tests for the deterministic decision rules, isolated from the pipeline."""

from __future__ import annotations

from app.models.claim import ClaimRequest, Document
from app.models.decision import Decision, DiagnosisMatch, RejectionReason
from app.rules.engine import adjudicate
from app.rules.financials import gather_bill_details
from app.rules.normalization import normalize_diagnosis
from tests.helpers import claim_request


def _decide(case_id: str, policy, degraded: bool = False):
    request = claim_request(case_id)
    member = policy.get_member(request.member_id)
    diagnosis = normalize_diagnosis(request, {}, policy)
    bill = gather_bill_details(request, policy, {})
    return adjudicate(request, member, diagnosis, policy, bill, {}, degraded)


def _decide_request(request: ClaimRequest, policy, degraded: bool = False):
    member = policy.get_member(request.member_id)
    diagnosis = normalize_diagnosis(request, {}, policy)
    bill = gather_bill_details(request, policy, {})
    return adjudicate(request, member, diagnosis, policy, bill, {}, degraded)


def _consultation(policy, **overrides) -> ClaimRequest:
    """A clean EMP001 consultation (Viral Fever, non-network), with overrides."""
    base = dict(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
        documents=[
            Document(
                file_id="F1", actual_type="PRESCRIPTION", content={"diagnosis": "Viral Fever"}
            ),
            Document(file_id="F2", actual_type="HOSPITAL_BILL", content={"total": 1500}),
        ],
    )
    base.update(overrides)
    return ClaimRequest(**base)


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
    r = adjudicate(request, None, DiagnosisMatch(), policy, bill, {}, False)
    assert r.decision is Decision.REJECTED
    assert RejectionReason.NOT_ELIGIBLE in r.rejection_reasons


# --- Phase 2 policy rules ----------------------------------------------------


def test_below_minimum_claim_amount_rejected(policy):
    # Policy minimum is 500; a 300 claim must be rejected as BELOW_MINIMUM.
    r = _decide_request(_consultation(policy, claimed_amount=300), policy)
    assert r.decision is Decision.REJECTED
    assert RejectionReason.BELOW_MINIMUM in r.rejection_reasons


def test_submission_after_deadline_rejected(policy):
    # Treatment 2024-11-01 + 30-day deadline; submitted 2024-12-20 is too late.
    r = _decide_request(
        _consultation(policy, submission_date="2024-12-20"), policy
    )
    assert r.decision is Decision.REJECTED
    assert RejectionReason.SUBMISSION_WINDOW_EXCEEDED in r.rejection_reasons


def test_submission_within_deadline_approved(policy):
    # Submitted 19 days after treatment — within the 30-day window.
    r = _decide_request(_consultation(policy, submission_date="2024-11-20"), policy)
    assert r.decision is Decision.APPROVED
    assert not r.rejection_reasons


def test_no_submission_date_is_treated_as_on_time(policy):
    r = _decide_request(_consultation(policy), policy)
    assert r.decision is Decision.APPROVED


def test_annual_opd_limit_exhausted_rejected(policy):
    # YTD claims already at the 50,000 annual OPD limit -> nothing left.
    r = _decide_request(_consultation(policy, ytd_claims_amount=50000), policy)
    assert r.decision is Decision.REJECTED
    assert RejectionReason.ANNUAL_LIMIT_EXCEEDED in r.rejection_reasons


def test_annual_opd_remaining_caps_the_payout(policy):
    # Only 1,000 of the annual OPD limit remains; a 1,500 consultation (after_copay
    # 1,350) must be capped to 1,000 and approved with a note.
    r = _decide_request(_consultation(policy, ytd_claims_amount=49000), policy)
    assert r.decision is Decision.APPROVED
    assert r.approved_amount == 1000
    assert r.financial_breakdown["remaining_annual_opd"] == 1000
    assert any("annual" in n.lower() for n in r.notes)


# --- Phase 3 composed confidence ---------------------------------------------


def _adjudicate_with(policy, *, degraded=False, extraction_confidence=1.0):
    req = _consultation(policy)
    member = policy.get_member(req.member_id)
    diagnosis = normalize_diagnosis(req, {}, policy)
    bill = gather_bill_details(req, policy, {})
    return adjudicate(req, member, diagnosis, policy, bill, {}, degraded, extraction_confidence)


def test_full_extraction_confidence_keeps_base_score(policy):
    r = _adjudicate_with(policy)  # extraction_confidence=1.0
    assert r.decision is Decision.APPROVED
    assert r.confidence == 0.95


def test_low_extraction_quality_lowers_confidence(policy):
    full = _adjudicate_with(policy, extraction_confidence=1.0)
    low = _adjudicate_with(policy, extraction_confidence=0.5)
    assert low.confidence < full.confidence
    assert low.decision is Decision.APPROVED  # 0.75 is still confident enough


def test_very_low_confidence_routes_to_manual_review(policy):
    # degraded (-0.30) + poor extraction (-0.28) drops below the 0.50 gate.
    r = _adjudicate_with(policy, degraded=True, extraction_confidence=0.3)
    assert r.confidence < 0.50
    assert r.decision is Decision.MANUAL_REVIEW
