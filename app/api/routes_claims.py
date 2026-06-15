"""Claim submission endpoints.

Two ways to submit, both running the SAME pipeline and returning the same shape:

- `POST /claims`        — JSON body (`ClaimRequest`). Documents may carry
                          pre-extracted `content` (the deterministic eval path).
- `POST /claims/upload` — multipart form with real image/PDF files. Each file's
                          bytes are attached to a `Document`; the pipeline
                          classifies and extracts them with Claude vision.

Outcome:
  - `BLOCKED`  : document verification stopped it (specific `blocking_issues`).
  - `DECIDED`  : the rule engine produced a `decision` (+ amount, reasons,
                 line items, confidence, explanation, financial breakdown).

Errors
------
- 422: body/form fails validation.
- 503: policy/graph unavailable (degraded startup) — never decide without a policy.
"""

from __future__ import annotations

import base64
import logging
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from app.models.claim import ClaimRequest, Document
from app.models.decision import ClaimProcessingResult, ProcessingStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["claims"])


def _run_pipeline(claim: ClaimRequest, request: Request) -> ClaimProcessingResult:
    """Resolve shared resources, run the graph, and assemble the response.

    Shared by both the JSON and multipart endpoints so they behave identically.
    """
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


@router.post("/claims", response_model=ClaimProcessingResult)
def submit_claim(claim: ClaimRequest, request: Request) -> ClaimProcessingResult:
    """Submit a claim as JSON (documents may carry pre-extracted `content`)."""
    return _run_pipeline(claim, request)


@router.post("/claims/upload", response_model=ClaimProcessingResult)
async def submit_claim_upload(
    request: Request,
    files: list[UploadFile] = File(..., description="One or more images/PDFs"),
    member_id: str = Form(...),
    policy_id: str = Form(...),
    claim_category: str = Form(...),
    treatment_date: str = Form(...),
    claimed_amount: float = Form(...),
    hospital_name: str | None = Form(None),
    ytd_claims_amount: float | None = Form(None),
    pre_authorization_obtained: bool = Form(False),
) -> ClaimProcessingResult:
    """Submit a claim with real uploaded documents (images/PDFs).

    The document type is NOT supplied by the caller — the pipeline classifies
    each file with vision and extracts its fields, then adjudicates as usual.
    """
    documents: list[Document] = []
    for index, upload in enumerate(files, start=1):
        raw = await upload.read()
        if not raw:
            continue
        documents.append(
            Document(
                file_id=f"F{index:03d}",
                file_name=upload.filename,
                media_type=upload.content_type,
                data_base64=base64.b64encode(raw).decode("ascii"),
                actual_type=None,  # resolved by the vision classifier
            )
        )

    if not documents:
        raise HTTPException(status_code=422, detail="At least one non-empty file is required.")

    try:
        claim = ClaimRequest(
            member_id=member_id,
            policy_id=policy_id,
            claim_category=claim_category,
            treatment_date=treatment_date,
            claimed_amount=claimed_amount,
            hospital_name=hospital_name,
            ytd_claims_amount=ytd_claims_amount,
            pre_authorization_obtained=pre_authorization_obtained,
            documents=documents,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return _run_pipeline(claim, request)
