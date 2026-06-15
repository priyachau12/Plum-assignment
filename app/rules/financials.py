"""Financial facts + the money computation.

Purpose
-------
Two jobs, both kept out of the rule engine so the engine reads clean values:
  1. Pull the money-relevant facts out of a claim's (possibly AI-read) content:
     the bill line items, and whether the treatment happened at a network hospital.
  2. Compute the approved amount: network discount FIRST, then co-pay, then caps
     (per-claim / sub-limit) — the order the policy specifies (TC010).

Why it exists
-------------
The decision rules should reason over clean typed values and delegate the
arithmetic, not dig through nested content dicts or inline the math. This module
is the one place that knows how the content is shaped and how the money is
computed.

Interactions
------------
- Called by `rules/engine.py` (via the adjudicate node).
- `extracted_content` maps file_id -> AI-read fields, used when a document has no
  inline `content` (real-document path). For the test cases, inline `content`
  is always present so `extracted_content` is empty.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.claim import ClaimRequest, Document
from app.models.policy import OpdCategory, Policy


class BillItem(BaseModel):
    description: str
    amount: float


class BillDetails(BaseModel):
    items: list[BillItem] = Field(default_factory=list)
    is_network_hospital: bool = False
    hospital_name: str | None = None


def get_document_fields(document: Document, extracted_content: dict[str, Any]) -> dict[str, Any]:
    """The usable fields for a document: its own content if present, else the
    fields the extractor pulled out."""
    return document.content or extracted_content.get(document.file_id) or {}


def list_bill_items(request: ClaimRequest, extracted_content: dict[str, Any]) -> list[BillItem]:
    items: list[BillItem] = []
    for doc in request.documents:
        fields = get_document_fields(doc, extracted_content)
        for raw in fields.get("line_items") or []:
            amount = raw.get("amount")
            if amount is None:
                continue
            items.append(
                BillItem(description=str(raw.get("description", "")).strip(), amount=float(amount))
            )
    return items


def find_network_hospital(
    request: ClaimRequest, policy: Policy, extracted_content: dict[str, Any]
) -> tuple[bool, str | None]:
    """True (+ the name) if the request's or any document's hospital is one of
    the policy's network hospitals (case-insensitive)."""
    candidates: list[str] = []
    if request.hospital_name:
        candidates.append(request.hospital_name)
    for doc in request.documents:
        name = get_document_fields(doc, extracted_content).get("hospital_name")
        if isinstance(name, str):
            candidates.append(name)

    network = {h.lower() for h in policy.network_hospitals}
    for name in candidates:
        if name.lower() in network:
            return True, name
    return False, (candidates[0] if candidates else None)


def gather_bill_details(
    request: ClaimRequest, policy: Policy, extracted_content: dict[str, Any]
) -> BillDetails:
    is_network, hospital = find_network_hospital(request, policy, extracted_content)
    return BillDetails(
        items=list_bill_items(request, extracted_content),
        is_network_hospital=is_network,
        hospital_name=hospital,
    )


def effective_per_claim_cap(cat: OpdCategory | None, policy: Policy) -> float:
    """The binding per-claim cap: the higher of the base per-claim limit and the
    category sub-limit. Some categories (e.g. dental at 10,000) allow more than
    the 5,000 base; consultation's sub-limit equals the base so the base binds.
    (This is a `max`, not a `min` — see TC010, which approves 3,240 for a
    consultation whose sub-limit is 2,000.)"""
    return max(policy.coverage.per_claim_limit, cat.sub_limit if cat else 0)


def compute_financials(
    covered_base: float,
    cat: OpdCategory | None,
    bill: BillDetails,
    policy: Policy,
) -> tuple[float, dict[str, Any]]:
    """Apply network discount FIRST, then co-pay, then cap at the effective
    per-claim limit. Returns (approved_amount, breakdown)."""
    discount_pct = cat.network_discount_percent if cat and bill.is_network_hospital else 0.0
    copay_pct = cat.copay_percent if cat else 0.0
    after_discount = covered_base * (1 - discount_pct / 100)
    after_copay = after_discount * (1 - copay_pct / 100)
    cap = effective_per_claim_cap(cat, policy)
    approved = round(min(after_copay, cap), 2)

    breakdown: dict[str, Any] = {
        "covered_base": round(covered_base, 2),
        "is_network": bill.is_network_hospital,
        "network_discount_percent": discount_pct,
        "after_network_discount": round(after_discount, 2),
        "copay_percent": copay_pct,
        "after_copay": round(after_copay, 2),
        "approved_amount": approved,
    }
    return approved, breakdown
