"""Bill details for the decision.

Purpose
-------
Pull the money-relevant facts out of a claim's (possibly AI-read) content: the
bill items, and whether the treatment happened at a network hospital.

Why it exists
-------------
The decision rules should reason over clean typed values, not dig through nested
content dicts. This module is the one place that knows how the content is shaped.

Interactions
------------
- Called by `rules/decision_rules.py` (via the decide-claim node).
- `read_fields` maps file_id -> AI-read fields, used when a document has no
  inline `content` (real-document path). For the test cases, inline `content`
  is always present so `read_fields` is empty.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.claim import ClaimRequest, Document
from app.models.policy import Policy


class BillItem(BaseModel):
    description: str
    amount: float


class BillDetails(BaseModel):
    items: list[BillItem] = Field(default_factory=list)
    is_network_hospital: bool = False
    hospital_name: str | None = None


def get_document_fields(document: Document, read_fields: dict[str, Any]) -> dict[str, Any]:
    """The usable fields for a document: its own content if present, else the
    fields the reader pulled out."""
    return document.content or read_fields.get(document.file_id) or {}


def list_bill_items(request: ClaimRequest, read_fields: dict[str, Any]) -> list[BillItem]:
    items: list[BillItem] = []
    for doc in request.documents:
        fields = get_document_fields(doc, read_fields)
        for raw in fields.get("line_items") or []:
            amount = raw.get("amount")
            if amount is None:
                continue
            items.append(
                BillItem(description=str(raw.get("description", "")).strip(), amount=float(amount))
            )
    return items


def find_network_hospital(
    request: ClaimRequest, policy: Policy, read_fields: dict[str, Any]
) -> tuple[bool, str | None]:
    """True (+ the name) if the request's or any document's hospital is one of
    the policy's network hospitals (case-insensitive)."""
    candidates: list[str] = []
    if request.hospital_name:
        candidates.append(request.hospital_name)
    for doc in request.documents:
        name = get_document_fields(doc, read_fields).get("hospital_name")
        if isinstance(name, str):
            candidates.append(name)

    network = {h.lower() for h in policy.network_hospitals}
    for name in candidates:
        if name.lower() in network:
            return True, name
    return False, (candidates[0] if candidates else None)


def gather_bill_details(
    request: ClaimRequest, policy: Policy, read_fields: dict[str, Any]
) -> BillDetails:
    is_network, hospital = find_network_hospital(request, policy, read_fields)
    return BillDetails(
        items=list_bill_items(request, read_fields),
        is_network_hospital=is_network,
        hospital_name=hospital,
    )
