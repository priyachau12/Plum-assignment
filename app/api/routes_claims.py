"""Claim submission endpoint.

`POST /claims` — accept a claim, run the pipeline, return the outcome:
  - `BLOCKED`  : document verification stopped it (specific `blocking_issues`).
  - `DECIDED`  : the rule engine produced a `decision` (+ amount, reasons,
                 line items, confidence, explanation, financial breakdown).

Errors
------
- 422 (automatic): body fails `ClaimRequest` validation.
- 503: policy/graph unavailable (degraded startup) — never decide without a policy.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, Request

from app.models.claim import ClaimRequest
from app.models.decision import ClaimProcessingResult, ProcessingStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["claims"])


@router.post("/claims", response_model=ClaimProcessingResult)
def submit_claim(claim: ClaimRequest, request: Request) -> ClaimProcessingResult:
    policy = getattr(request.app.state, "policy", None)
    graph = getattr(request.app.state, "graph", None)
    if policy is None or graph is None:
        raise HTTPException(
            status_code=503,
            detail="Policy not loaded; the system cannot process claims right now.",
        )

    claim_id = "CLM_" + uuid.uuid4().hex[:8].upper()
    logger.info("Processing claim %s for member %s", claim_id, claim.member_id)

    final_state = graph.invoke({"claim_id": claim_id, "request": claim})

    blocking_issues = final_state.get("blocking_issues", [])
    trace = final_state.get("trace", [])
    degraded = final_state.get("degraded", False)

    if blocking_issues:
        return ClaimProcessingResult(
            claim_id=claim_id,
            status=ProcessingStatus.BLOCKED,
            decision=None,
            blocking_issues=blocking_issues,
            degraded=degraded,
            note="Claim stopped at document verification. See blocking_issues for what to fix.",
            trace=trace,
        )

    result = final_state["decision_details"]
    return ClaimProcessingResult(
        claim_id=claim_id,
        status=ProcessingStatus.DECIDED,
        decision=result.decision,
        approved_amount=result.approved_amount,
        rejection_reasons=[r.value for r in result.rejection_reasons],
        line_items=result.line_items,
        confidence=result.confidence,
        degraded=degraded,
        explanation=final_state.get("explanation"),
        financial_breakdown=result.financial_breakdown,
        note=" ".join(result.notes) or None,
        trace=trace,
    )
