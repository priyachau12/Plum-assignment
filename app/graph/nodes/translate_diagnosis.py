"""translate_diagnosis node.

Turns the claim's free-text diagnosis/treatment into the policy's vocabulary
(a waiting-period key and/or an exclusion phrase) so the decision rules can
reason deterministically. Keeping it as its own step makes the trace explicit
("what did the system think the diagnosis was?").

- Bound to the loaded `policy` in `graph/builder.py`.
- Calls `rules.diagnosis_matcher.match_diagnosis`; writes `diagnosis_match` + trace.
"""

from __future__ import annotations

import logging

from app.graph.state import ClaimState
from app.models.decision import TraceEntry, TraceStatus
from app.models.policy import Policy
from app.rules.diagnosis_matcher import match_diagnosis

logger = logging.getLogger(__name__)


def translate_diagnosis(state: ClaimState, *, policy: Policy) -> dict:
    request = state["request"]
    read_fields = state.get("read_fields", {})
    match = match_diagnosis(request, read_fields, policy)
    logger.info(
        "translate_diagnosis: waiting=%s excluded=%s",
        match.waiting_condition,
        match.excluded_condition,
    )
    return {
        "diagnosis_match": match,
        "trace": [
            TraceEntry(
                step="translate_diagnosis",
                status=TraceStatus.OK,
                detail=(
                    f"diagnosis/treatment='{match.raw_text}' -> "
                    f"waiting_condition={match.waiting_condition}, "
                    f"excluded_condition={match.excluded_condition}"
                ),
                data={
                    "waiting_condition": match.waiting_condition,
                    "excluded_condition": match.excluded_condition,
                },
            )
        ],
    }
