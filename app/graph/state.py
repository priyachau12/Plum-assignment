"""Pipeline state — the clipboard that travels with each claim.

The single typed object that flows through every step. `total=False` => every
key is optional (state fills in as it goes). `trace` and `blocking_issues` use
`operator.add` so each step returns only its own new entries and LangGraph
concatenates them.

Field ownership:
    find_member         -> member
    label_documents     -> document_types
    check_documents     -> blocking_issues, status (BLOCKED)
    read_documents      -> read_fields, degraded
    translate_diagnosis -> diagnosis_match
    decide_claim        -> decision_details, status (DECIDED)
    write_explanation   -> explanation
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
    document_types: dict[str, str]
    read_fields: dict[str, Any]
    diagnosis_match: DiagnosisMatch
    degraded: bool
    decision_details: DecisionResult
    explanation: str
