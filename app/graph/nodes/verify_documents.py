"""verify_documents node — the early-stop gate.

Thin adapter over the pure `verify_documents` logic. It runs the checks,
appends their trace notes, surfaces any blocking issues, and — if the claim is
blocked — sets `status = BLOCKED` so the builder's fork routes the claim
straight to the end (skipping everything downstream).

- Bound to the loaded `policy` in `graph/builder.py`.
- Calls `verification.document_verifier.verify_documents`.
- Returns `{"trace": [...], "blocking_issues": [...], "status"?: BLOCKED}`.
"""

from __future__ import annotations

import logging

from app.graph.state import ClaimState
from app.models.decision import ProcessingStatus
from app.models.policy import Policy
from app.verification.document_verifier import verify_documents as run_verification

logger = logging.getLogger(__name__)


def verify_documents(state: ClaimState, *, policy: Policy) -> dict:
    request = state["request"]
    result = run_verification(request, policy)

    logger.info(
        "verify_documents: passed=%s blocking_issues=%d",
        result.passed,
        len(result.blocking_issues),
    )

    update: dict = {
        "trace": result.trace_entries,
        "blocking_issues": result.blocking_issues,
    }
    if not result.passed:
        update["status"] = ProcessingStatus.BLOCKED
    return update
