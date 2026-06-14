"""write_explanation node (AI-allowed) — turns the decision into member-facing text.

Always builds a deterministic, factual explanation from the decision. If the AI
is configured, it may rephrase it more naturally — but never changes the numbers
or the decision, and falls back to the built text on any failure.

- Bound to the (optional) `llm` client in `graph/builder.py`.
- Reads `decision_details`; writes `explanation` + trace.
"""

from __future__ import annotations

import logging

from app.graph.state import ClaimState
from app.llm.client import LLMClient, LLMError
from app.models.decision import Decision, DecisionResult, TraceEntry, TraceStatus

logger = logging.getLogger(__name__)


def _build_explanation_text(result: DecisionResult) -> str:
    d = result.decision
    if d is Decision.APPROVED:
        b = result.financial_breakdown
        parts = [f"Your claim was APPROVED for {result.approved_amount:.0f}."]
        if b.get("is_network") and b.get("network_discount_percent"):
            parts.append(
                f"A {b['network_discount_percent']:.0f}% network discount was applied first "
                f"({b['covered_base']:.0f} -> {b['after_network_discount']:.0f}),"
            )
        if b.get("copay_percent"):
            parts.append(f"then a {b['copay_percent']:.0f}% co-pay (-> {b['after_copay']:.0f}).")
        return " ".join(parts)
    if d is Decision.PARTIAL:
        covered = [li for li in result.line_items if li.covered]
        rejected = [li for li in result.line_items if not li.covered]
        approved_list = ", ".join(f"{li.description} ({li.amount:.0f})" for li in covered)
        rejected_list = ", ".join(f"{li.description} ({li.amount:.0f})" for li in rejected)
        return (
            f"Your claim was PARTIALLY approved for {result.approved_amount:.0f}. "
            f"Approved: {approved_list}. "
            f"Not approved: {rejected_list} — excluded under the policy."
        )
    if d is Decision.REJECTED:
        reasons = ", ".join(r.value for r in result.rejection_reasons)
        note = " ".join(result.notes)
        return f"Your claim was REJECTED ({reasons}). {note}".strip()
    # MANUAL_REVIEW
    return ("Your claim has been routed to MANUAL REVIEW. " + " ".join(result.notes)).strip()


def write_explanation(state: ClaimState, *, llm: LLMClient | None) -> dict:
    result = state.get("decision_details")
    if result is None:
        return {
            "trace": [
                TraceEntry(
                    step="write_explanation",
                    status=TraceStatus.SKIPPED,
                    detail="No decision to explain.",
                )
            ]
        }

    text = _build_explanation_text(result)
    source = "template"

    if llm is not None:
        try:
            text = llm.write_explanation(
                decision=result.decision.value,
                approved_amount=result.approved_amount,
                reasons=[r.value for r in result.rejection_reasons],
                fallback=text,
            )
            source = "llm"
        except LLMError as exc:
            logger.warning("write_explanation: AI failed, using built text: %s", exc)

    return {
        "explanation": text,
        "trace": [
            TraceEntry(
                step="write_explanation",
                status=TraceStatus.OK,
                detail=f"Generated member-facing explanation ({source}).",
                data={"source": source},
            )
        ],
    }
