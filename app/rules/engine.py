"""The deterministic decision rules (the rulebook).

Purpose
-------
Given a validated claim, the resolved member, the normalized diagnosis, the
policy, and the bill details, apply an ORDERED set of rules and return a single
`DecisionResult` (verdict + approved amount + per-line breakdown + confidence +
a trace of every rule that ran).

Why it exists
-------------
This is the system's brain: pure, reproducible, unit-testable. No AI. The order
encodes precedence; every rule writes a trace note whether or not it changes the
outcome, so the reviewer can see everything that was checked.

Rule order (precedence)
-----------------------
 1. Eligibility (member exists)                       -> REJECT NOT_ELIGIBLE
 2. Whole-claim exclusion (diagnosis/treatment)       -> REJECT EXCLUDED_CONDITION   (TC012)
 3. Waiting period (specific, then initial)           -> REJECT WAITING_PERIOD        (TC005)
 4. Pre-authorization (high-value tests)              -> REJECT PRE_AUTH_MISSING      (TC007)
 5. Per-claim limit (on covered amount)               -> REJECT PER_CLAIM_EXCEEDED    (TC008)
 6. Line-item exclusions (dental/vision)              -> PARTIAL / REJECT             (TC006)
 7. Fraud signals                                     -> MANUAL_REVIEW                (TC009)
 8. High-value auto review                            -> MANUAL_REVIEW
 9. Money math (discount BEFORE co-pay)               -> APPROVED amount        (TC004, TC010)

Interactions
------------
- Called by the `adjudicate` node with inputs assembled from state.
- Returns `DecisionResult` (models/decision.py).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.models.claim import ClaimRequest
from app.models.decision import (
    Decision,
    DecisionResult,
    DiagnosisMatch,
    LineItemDecision,
    RejectionReason,
    TraceEntry,
    TraceStatus,
)
from app.models.policy import Member, OpdCategory, Policy
from app.rules.financials import (
    BillDetails,
    compute_financials,
    effective_per_claim_cap,
    get_document_fields,
)

_LINE_ITEM_CATEGORIES = {"DENTAL", "VISION"}


def _confidence_score(degraded: bool, base: float = 0.95) -> float:
    return round(max(0.0, base - (0.30 if degraded else 0.0)), 2)


def _find_fraud_signals(request: ClaimRequest, policy: Policy) -> list[str]:
    limits = policy.fraud_thresholds
    signals: list[str] = []

    same_day = [h for h in request.claims_history if h.claim_date == request.treatment_date]
    same_day_count = len(same_day) + 1  # + this claim
    if same_day_count > limits.same_day_claims_limit:
        signals.append(
            f"SAME_DAY_CLAIMS: {same_day_count} claims on "
            f"{request.treatment_date.isoformat()} exceeds limit of {limits.same_day_claims_limit}"
        )

    this_month = [
        h
        for h in request.claims_history
        if h.claim_date
        and (h.claim_date.year, h.claim_date.month)
        == (request.treatment_date.year, request.treatment_date.month)
    ]
    month_count = len(this_month) + 1
    if month_count > limits.monthly_claims_limit:
        signals.append(
            f"MONTHLY_CLAIMS: {month_count} claims this month exceeds limit "
            f"of {limits.monthly_claims_limit}"
        )

    if request.claimed_amount >= limits.high_value_claim_threshold:
        signals.append(
            f"HIGH_VALUE: amount {request.claimed_amount} >= threshold "
            f"{limits.high_value_claim_threshold}"
        )
    return signals


def _collect_test_text(request: ClaimRequest, extracted_content: dict[str, Any]) -> str:
    parts: list[str] = []
    for doc in request.documents:
        fields = get_document_fields(doc, extracted_content)
        for key in ("tests_ordered", "test_name", "diagnosis", "treatment"):
            value = fields.get(key)
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts.extend(str(v) for v in value)
        for raw in fields.get("line_items") or []:
            parts.append(str(raw.get("description", "")))
    return " | ".join(parts).lower()


def adjudicate(
    request: ClaimRequest,
    member: Member | None,
    diagnosis: DiagnosisMatch,
    policy: Policy,
    bill: BillDetails,
    extracted_content: dict[str, Any],
    degraded: bool,
) -> DecisionResult:
    trace: list[TraceEntry] = []
    category = request.claim_category.value
    cat: OpdCategory | None = policy.get_category(category)

    def record(step: str, status: TraceStatus, detail: str, data: dict | None = None) -> None:
        trace.append(TraceEntry(step=step, status=status, detail=detail, data=data or {}))

    def rejected(reason: RejectionReason, notes: list[str]) -> DecisionResult:
        return DecisionResult(
            decision=Decision.REJECTED,
            approved_amount=0.0,
            rejection_reasons=[reason],
            line_items=line_items,
            confidence=_confidence_score(degraded),
            notes=notes,
            trace_entries=trace,
        )

    # ---- Pre-compute line items / covered base ------------------------------
    line_items: list[LineItemDecision] = []
    any_excluded = False
    any_covered = False

    if category in _LINE_ITEM_CATEGORIES and cat and bill.items:
        excluded_terms = [p.lower() for p in (cat.excluded_procedures + cat.excluded_items)]
        covered_base = 0.0
        for item in bill.items:
            desc = item.description.lower()
            is_excluded = any(term and term in desc for term in excluded_terms)
            if is_excluded:
                any_excluded = True
                line_items.append(
                    LineItemDecision(
                        description=item.description,
                        amount=item.amount,
                        covered=False,
                        reason="Excluded procedure under this policy",
                    )
                )
            else:
                any_covered = True
                covered_base += item.amount
                line_items.append(
                    LineItemDecision(description=item.description, amount=item.amount, covered=True)
                )
    else:
        covered_base = request.claimed_amount
        any_covered = True

    # ---- Rule 1: eligibility -------------------------------------------------
    if member is None:
        record(
            "adjudicate.eligibility",
            TraceStatus.BLOCKED,
            f"Member {request.member_id} is not on the policy roster.",
        )
        return rejected(
            RejectionReason.NOT_ELIGIBLE,
            [f"Member {request.member_id} is not covered under {policy.policy_id}."],
        )
    record(
        "adjudicate.eligibility",
        TraceStatus.OK,
        f"Member {member.member_id} ({member.name}) is covered.",
    )

    # ---- Rule 2: whole-claim exclusion --------------------------------------
    if diagnosis.excluded_condition:
        record(
            "adjudicate.exclusions",
            TraceStatus.BLOCKED,
            f"Diagnosis/treatment matches a policy exclusion: '{diagnosis.excluded_condition}'.",
        )
        return rejected(
            RejectionReason.EXCLUDED_CONDITION,
            [f"This claim is for an excluded condition: '{diagnosis.excluded_condition}'."],
        )
    record(
        "adjudicate.exclusions",
        TraceStatus.OK,
        "No policy exclusion matched the diagnosis/treatment.",
    )

    # ---- Rule 3: waiting period ---------------------------------------------
    if member.join_date:
        waiting = policy.waiting_periods
        if diagnosis.waiting_condition:
            days = waiting.specific_conditions.get(diagnosis.waiting_condition, 0)
            eligible = member.join_date + timedelta(days=days)
            if request.treatment_date < eligible:
                record(
                    "adjudicate.waiting_period",
                    TraceStatus.BLOCKED,
                    f"'{diagnosis.waiting_condition}' has a {days}-day waiting period; "
                    f"member joined {member.join_date.isoformat()}, eligible from "
                    f"{eligible.isoformat()}, treatment on {request.treatment_date.isoformat()}.",
                )
                return rejected(
                    RejectionReason.WAITING_PERIOD,
                    [
                        f"Within the {days}-day waiting period for "
                        f"'{diagnosis.waiting_condition}'. Eligible from {eligible.isoformat()}."
                    ],
                )
        eligible_initial = member.join_date + timedelta(days=waiting.initial_waiting_period_days)
        if request.treatment_date < eligible_initial:
            record(
                "adjudicate.waiting_period",
                TraceStatus.BLOCKED,
                f"Initial {waiting.initial_waiting_period_days}-day waiting period; "
                f"eligible from {eligible_initial.isoformat()}.",
            )
            return rejected(
                RejectionReason.WAITING_PERIOD,
                [
                    f"Within the initial {waiting.initial_waiting_period_days}-day waiting period. "
                    f"Eligible from {eligible_initial.isoformat()}."
                ],
            )
    record("adjudicate.waiting_period", TraceStatus.OK, "Outside all applicable waiting periods.")

    # ---- Rule 4: pre-authorization ------------------------------------------
    high_value_tests = (cat.high_value_tests_requiring_pre_auth if cat else []) or []
    if high_value_tests:
        text = _collect_test_text(request, extracted_content)
        found = [test for test in high_value_tests if test.lower() in text]
        threshold = (cat.pre_auth_threshold if cat else None) or 0
        if found and request.claimed_amount > threshold and not request.pre_authorization_obtained:
            record(
                "adjudicate.pre_auth",
                TraceStatus.BLOCKED,
                f"{', '.join(found)} above {threshold} requires pre-authorization; none provided.",
            )
            return rejected(
                RejectionReason.PRE_AUTH_MISSING,
                [
                    f"Pre-authorization is required for {', '.join(found)} above "
                    f"{threshold:.0f} and was not obtained. Obtain pre-auth and resubmit."
                ],
            )
    record("adjudicate.pre_auth", TraceStatus.OK, "No pre-authorization requirement triggered.")

    # ---- Rule 5: per-claim limit (on the covered amount) --------------------
    per_claim_cap = effective_per_claim_cap(cat, policy)
    if covered_base > per_claim_cap:
        record(
            "adjudicate.per_claim_limit",
            TraceStatus.BLOCKED,
            f"Covered amount {covered_base:.0f} exceeds the per-claim limit of "
            f"{policy.coverage.per_claim_limit:.0f}.",
        )
        return rejected(
            RejectionReason.PER_CLAIM_EXCEEDED,
            [
                f"The per-claim limit is {policy.coverage.per_claim_limit:.0f}; this claim is "
                f"for {request.claimed_amount:.0f}."
            ],
        )
    record(
        "adjudicate.per_claim_limit",
        TraceStatus.OK,
        f"Covered amount {covered_base:.0f} is within the limit of {per_claim_cap:.0f}.",
    )

    # ---- Rule 6: all line items excluded ------------------------------------
    if category in _LINE_ITEM_CATEGORIES and bill.items and not any_covered:
        record(
            "adjudicate.line_items",
            TraceStatus.BLOCKED,
            "Every line item is an excluded procedure.",
        )
        return rejected(
            RejectionReason.EXCLUDED_CONDITION, ["All claimed procedures are excluded."]
        )

    # ---- Rule 7: fraud signals ----------------------------------------------
    signals = _find_fraud_signals(request, policy)
    if signals:
        record("adjudicate.fraud", TraceStatus.BLOCKED, "; ".join(signals), {"signals": signals})
        return DecisionResult(
            decision=Decision.MANUAL_REVIEW,
            approved_amount=0.0,
            line_items=line_items,
            confidence=_confidence_score(degraded, base=0.90),
            notes=["Routed to manual review due to fraud signals: " + "; ".join(signals)],
            financial_breakdown={"signals": signals},
            trace_entries=trace,
        )
    record("adjudicate.fraud", TraceStatus.OK, "No fraud signals.")

    # ---- Rule 8: high-value auto manual review ------------------------------
    if request.claimed_amount > policy.fraud_thresholds.auto_manual_review_above:
        record(
            "adjudicate.high_value",
            TraceStatus.BLOCKED,
            f"Amount {request.claimed_amount:.0f} exceeds auto-review threshold "
            f"{policy.fraud_thresholds.auto_manual_review_above:.0f}.",
        )
        return DecisionResult(
            decision=Decision.MANUAL_REVIEW,
            approved_amount=0.0,
            line_items=line_items,
            confidence=_confidence_score(degraded, base=0.90),
            notes=["High-value claim routed to manual review."],
            trace_entries=trace,
        )

    # ---- Rule 9: money math (network discount BEFORE co-pay) ----------------
    approved, breakdown = compute_financials(covered_base, cat, bill, policy)
    notes: list[str] = []
    if degraded:
        notes.append(
            "A processing component failed and was skipped; manual review is recommended "
            "due to incomplete processing."
        )
    record(
        "adjudicate.financials",
        TraceStatus.OK,
        f"covered {breakdown['covered_base']:.0f} -> network discount "
        f"{breakdown['network_discount_percent']:.0f}% -> "
        f"{breakdown['after_network_discount']:.0f} -> co-pay "
        f"{breakdown['copay_percent']:.0f}% -> approved {approved:.0f}.",
        breakdown,
    )

    return DecisionResult(
        decision=Decision.PARTIAL if any_excluded else Decision.APPROVED,
        approved_amount=approved,
        line_items=line_items,
        confidence=_confidence_score(degraded),
        financial_breakdown=breakdown,
        notes=notes,
        trace_entries=trace,
    )
