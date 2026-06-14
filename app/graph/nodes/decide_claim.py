"""decide_claim node — runs the deterministic decision rules.

Assembles the rules' inputs from state, runs `rules.decision_rules.apply_rules`,
and stores the result + its trace. This node is thin; all logic lives in the
pure, tested rulebook.

- Bound to the loaded `policy` in `graph/builder.py`.
- Reads `request`, `member`, `diagnosis_match`, `read_fields`, `degraded`.
- Writes `decision_details`, `status=DECIDED`, and the rules' trace entries.
"""

from __future__ import annotations

import logging

from app.graph.state import ClaimState
from app.models.decision import DiagnosisMatch, ProcessingStatus
from app.models.policy import Policy
from app.rules.bill_details import gather_bill_details
from app.rules.decision_rules import apply_rules

logger = logging.getLogger(__name__)


def decide_claim(state: ClaimState, *, policy: Policy) -> dict:
    request = state["request"]
    member = state.get("member")
    diagnosis = state.get("diagnosis_match") or DiagnosisMatch()
    read_fields = state.get("read_fields", {})
    degraded = state.get("degraded", False)

    bill = gather_bill_details(request, policy, read_fields)
    result = apply_rules(request, member, diagnosis, policy, bill, read_fields, degraded)

    logger.info(
        "decide_claim: decision=%s approved=%s confidence=%s",
        result.decision.value,
        result.approved_amount,
        result.confidence,
    )
    return {
        "decision_details": result,
        "status": ProcessingStatus.DECIDED,
        "trace": result.trace_entries,
    }
