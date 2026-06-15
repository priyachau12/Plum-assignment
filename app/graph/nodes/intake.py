"""intake node — the pipeline's first step.

Opens the audit trail and looks up the member in the loaded policy. It does not
decide anything; it records context every later step (and the reviewer) relies
on (does this member exist, does the claim's policy match the loaded one).

- Bound to the loaded `policy` via `functools.partial` in `graph/builder.py`.
- Returns `{"member": ..., "trace": [...]}` which LangGraph merges into state.
"""

from __future__ import annotations

import logging

from app.graph.state import ClaimState
from app.models.decision import TraceEntry, TraceStatus
from app.models.policy import Policy

logger = logging.getLogger(__name__)


def intake(state: ClaimState, *, policy: Policy) -> dict:
    request = state["request"]
    member = policy.get_member(request.member_id)

    logger.info(
        "intake: member=%s category=%s amount=%s docs=%d",
        request.member_id,
        request.claim_category.value,
        request.claimed_amount,
        len(request.documents),
    )

    entries: list[TraceEntry] = [
        TraceEntry(
            step="intake",
            status=TraceStatus.OK,
            detail=(
                f"Claim received for member {request.member_id}, category "
                f"{request.claim_category.value}, claimed amount "
                f"{request.claimed_amount}, with {len(request.documents)} document(s)."
            ),
            data={
                "member_found": member is not None,
                "claim_category": request.claim_category.value,
            },
        )
    ]

    if member is None:
        entries.append(
            TraceEntry(
                step="intake.lookup",
                status=TraceStatus.FAILED,
                detail=f"Member {request.member_id} was not found in the policy roster.",
            )
        )
    elif request.policy_id != policy.policy_id:
        entries.append(
            TraceEntry(
                step="intake.policy_match",
                status=TraceStatus.FAILED,
                detail=(
                    f"Claim policy_id '{request.policy_id}' does not match the loaded "
                    f"policy '{policy.policy_id}'."
                ),
            )
        )

    return {"member": member, "trace": entries}
