"""explain node (AI-allowed) — turns the decision into member-facing text.

Always builds a deterministic, factual explanation from the decision. If the AI
is configured, it may rephrase it more naturally — but never changes the numbers
or the decision, and falls back to the built text on any failure.

- Bound to the (optional) `llm` client in `graph/builder.py`.
- Reads `adjudication_result`; writes `explanation` + trace.
"""

from __future__ import annotations

import logging
import re

from app.graph.state import ClaimState
from app.llm.client import LLMClient, LLMError
from app.models.decision import Decision, DecisionResult, TraceEntry, TraceStatus

logger = logging.getLogger(__name__)


def _build_explanation_text(result: DecisionResult) -> str:
    d = result.decision
    note = " ".join(result.notes).strip()  # e.g. degraded / capped caveats
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
        if note:  # surface degraded/manual-review caveats on approvals too
            parts.append(note)
        return " ".join(parts)
    if d is Decision.PARTIAL:
        covered = [li for li in result.line_items if li.covered]
        rejected = [li for li in result.line_items if not li.covered]
        approved_list = ", ".join(f"{li.description} ({li.amount:.0f})" for li in covered)
        rejected_list = ", ".join(f"{li.description} ({li.amount:.0f})" for li in rejected)
        base = (
            f"Your claim was PARTIALLY approved for {result.approved_amount:.0f}. "
            f"Approved: {approved_list}. "
            f"Not approved: {rejected_list} — excluded under the policy."
        )
        return f"{base} {note}".strip()
    if d is Decision.REJECTED:
        reasons = ", ".join(r.value for r in result.rejection_reasons)
        return f"Your claim was REJECTED ({reasons}). {note}".strip()
    # MANUAL_REVIEW
    return ("Your claim has been routed to MANUAL REVIEW. " + note).strip()


def _is_consistent_with_decision(text: str, result: DecisionResult) -> bool:
    """Guard against an LLM explanation that drifts from the decision. For a
    payout (APPROVED/PARTIAL) the approved amount must actually appear in the
    text; if it doesn't, we don't trust the rephrasing. Non-payout decisions
    (amount 0) are not amount-checked, so the guard never false-triggers on them.

    Numbers are parsed and compared numerically — not as substrings — so '1,350'
    matches 1350.0, a decimal payout (e.g. 899.50) isn't lost to integer
    rounding, and an approved 350 does NOT spuriously match an AI-quoted '1,350'.
    """
    if result.decision not in (Decision.APPROVED, Decision.PARTIAL):
        return True
    target = round(result.approved_amount, 2)
    for token in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            if abs(float(token.replace(",", "")) - target) < 0.01:
                return True
        except ValueError:
            continue
    return False


def explain(state: ClaimState, *, llm: LLMClient | None) -> dict:
    result = state.get("adjudication_result")
    if result is None:
        return {
            "trace": [
                TraceEntry(
                    step="explain",
                    status=TraceStatus.SKIPPED,
                    detail="No decision to explain.",
                )
            ]
        }

    text = _build_explanation_text(result)
    source = "template"

    if llm is not None:
        try:
            ai_text = llm.generate_explanation(
                decision=result.decision.value,
                approved_amount=result.approved_amount,
                reasons=[r.value for r in result.rejection_reasons],
                fallback=text,
            )
        except LLMError as exc:
            logger.warning("explain: AI failed, using built text: %s", exc)
        else:
            # Only trust the rephrasing if it agrees with the decision's numbers.
            if _is_consistent_with_decision(ai_text, result):
                text = ai_text
                source = "llm"
            else:
                logger.warning(
                    "explain: AI text did not match the approved amount; using built text."
                )
                source = "template-guarded"

    return {
        "explanation": text,
        "trace": [
            TraceEntry(
                step="explain",
                status=TraceStatus.OK,
                detail=f"Generated member-facing explanation ({source}).",
                data={"source": source},
            )
        ],
    }
