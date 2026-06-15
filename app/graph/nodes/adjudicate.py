"""adjudicate node — runs the deterministic decision rules.

Assembles the rules' inputs from state, runs `rules.engine.adjudicate`,
and stores the result + its trace. This node is thin; all logic lives in the
pure, tested rulebook.

- Bound to the loaded `policy` in `graph/builder.py`.
- Reads `request`, `member`, `normalized_diagnosis`, `extracted_content`, `degraded`.
- Writes `adjudication_result`, `status=DECIDED`, and the rules' trace entries.
"""

from __future__ import annotations

import logging

from app.graph.state import ClaimState
from app.models.decision import DiagnosisMatch, ProcessingStatus
from app.models.policy import Policy
from app.rules.engine import adjudicate as run_adjudication
from app.rules.financials import gather_bill_details

logger = logging.getLogger(__name__)


def adjudicate(state: ClaimState, *, policy: Policy) -> dict:
    request = state["request"]
    member = state.get("member")
    diagnosis = state.get("normalized_diagnosis") or DiagnosisMatch()
    extracted_content = state.get("extracted_content", {})
    degraded = state.get("degraded", False)

    bill = gather_bill_details(request, policy, extracted_content)
    result = run_adjudication(
        request, member, diagnosis, policy, bill, extracted_content, degraded
    )

    logger.info(
        "adjudicate: decision=%s approved=%s confidence=%s",
        result.decision.value,
        result.approved_amount,
        result.confidence,
    )
    return {
        "adjudication_result": result,
        "status": ProcessingStatus.DECIDED,
        "trace": result.trace_entries,
    }
