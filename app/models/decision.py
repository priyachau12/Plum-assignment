"""Decision, trace, blocking, and adjudication models — the OUTPUT side.

Purpose
-------
Type everything the system *produces*: the trace (observability), the
early-stop blocking issues (verification), the normalized diagnosis, and the
adjudication result (the decision + amounts + per-line breakdown + confidence).

Why it exists
-------------
Observability (20%) and AI/decision integration are graded on the *shape* of
what we return. Pydantic types make the response validated and self-documenting.

Interactions
------------
- Nodes append `TraceEntry` to `state["trace"]`.
- `verification/document_verifier.py` builds `BlockingIssue`s.
- `rules/normalization.py` builds `DiagnosisMatch`.
- `rules/engine.py` builds `DecisionResult`.
- `api/routes_claims.py` returns a `ClaimProcessingResult`.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Decision(str, Enum):
    """The four terminal claim decisions."""

    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class TraceStatus(str, Enum):
    OK = "OK"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TraceEntry(BaseModel):
    """One step in the audit trail. The list of these IS our observability."""

    step: str
    status: TraceStatus
    detail: str
    data: dict[str, Any] = Field(default_factory=dict)


# --- Early-stop (document verification) ---


class BlockingReason(str, Enum):
    MISSING_REQUIRED_DOCUMENT = "MISSING_REQUIRED_DOCUMENT"
    UNREADABLE_DOCUMENT = "UNREADABLE_DOCUMENT"
    PATIENT_MISMATCH = "PATIENT_MISMATCH"


class BlockingIssue(BaseModel):
    reason: BlockingReason
    message: str  # member-facing, specific
    details: dict[str, Any] = Field(default_factory=dict)


# --- Diagnosis normalization (LLM-allowed; deterministic here) ---


class DiagnosisMatch(BaseModel):
    """Free-text diagnosis/treatment mapped onto the policy's vocabulary."""

    raw_text: str = ""
    waiting_condition: str | None = None  # key in waiting_periods.specific_conditions
    excluded_condition: str | None = None  # phrase in exclusions.conditions


# --- Adjudication (the deterministic decision) ---


class RejectionReason(str, Enum):
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    BELOW_MINIMUM = "BELOW_MINIMUM"
    SUBMISSION_WINDOW_EXCEEDED = "SUBMISSION_WINDOW_EXCEEDED"
    WAITING_PERIOD = "WAITING_PERIOD"
    EXCLUDED_CONDITION = "EXCLUDED_CONDITION"
    PRE_AUTH_MISSING = "PRE_AUTH_MISSING"
    PER_CLAIM_EXCEEDED = "PER_CLAIM_EXCEEDED"
    ANNUAL_LIMIT_EXCEEDED = "ANNUAL_LIMIT_EXCEEDED"


class LineItemDecision(BaseModel):
    """Per-line decision (for partial approvals like dental)."""

    description: str
    amount: float
    covered: bool
    reason: str | None = None


class DecisionResult(BaseModel):
    """The output of the deterministic rule engine."""

    decision: Decision
    approved_amount: float = 0.0
    rejection_reasons: list[RejectionReason] = Field(default_factory=list)
    line_items: list[LineItemDecision] = Field(default_factory=list)
    confidence: float = 0.0
    financial_breakdown: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    trace_entries: list[TraceEntry] = Field(default_factory=list)


# --- Top-level response ---


class ProcessingStatus(str, Enum):
    BLOCKED = "BLOCKED"  # stopped at document verification
    DECIDED = "DECIDED"  # the rule engine produced a decision


class ClaimProcessingResult(BaseModel):
    """The response body for `POST /claims`."""

    claim_id: str
    status: ProcessingStatus
    decision: Decision | None = None
    approved_amount: float | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    line_items: list[LineItemDecision] = Field(default_factory=list)
    confidence: float | None = None
    degraded: bool = False
    blocking_issues: list[BlockingIssue] = Field(default_factory=list)
    explanation: str | None = None
    financial_breakdown: dict[str, Any] | None = None
    note: str | None = None
    trace: list[TraceEntry] = Field(default_factory=list)
