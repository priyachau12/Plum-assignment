"""Pipeline state — the clipboard that travels with each claim.

The single typed object that flows through every step. `total=False` => every
key is optional (state fills in as it goes). `trace` and `blocking_issues` use
`operator.add` so each step returns only its own new entries and LangGraph
concatenates them.

Field ownership:
    intake              -> member
    classify            -> classified_docs
    verify_documents    -> blocking_issues, status (BLOCKED)
    extract             -> extracted_content, degraded
    normalize_diagnosis -> normalized_diagnosis
    adjudicate          -> adjudication_result, status (DECIDED)
    explain             -> explanation
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.models.claim import ClaimRequest
from app.models.decision import (
    BlockingIssue,
    DecisionResult,
    DiagnosisMatch,
    ProcessingStatus,
    TraceEntry,
)
from app.models.policy import Member


class ClaimState(TypedDict, total=False):
    claim_id: str
    request: ClaimRequest
    member: Member | None
    status: ProcessingStatus
    trace: Annotated[list[TraceEntry], operator.add]
    blocking_issues: Annotated[list[BlockingIssue], operator.add]

    # Working fields filled in as the claim moves down the line.
    classified_docs: dict[str, str]
    extracted_content: dict[str, Any]
    normalized_diagnosis: DiagnosisMatch
    degraded: bool
    adjudication_result: DecisionResult
    explanation: str
