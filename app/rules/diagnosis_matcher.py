"""Diagnosis matcher.

Purpose
-------
Match a free-text diagnosis/treatment (e.g. "Type 2 Diabetes Mellitus", "Morbid
Obesity — BMI 37 / Bariatric Consultation") to the policy's controlled
vocabulary: a `waiting_periods.specific_conditions` key and/or an
`exclusions.conditions` phrase. The decision rules then reason over those keys.

Why deterministic (the assignment allows an LLM here)
-----------------------------------------------------
The decision must be reproducible, so the *vocabulary* is fixed (it comes from
the policy) and matching is keyword-based. An LLM can be added as a fallback for
text the keyword table doesn't cover, but its answer would still be checked
against this same vocabulary before the rules trust it. For the 12 test cases
the keyword table resolves everything, so the eval is deterministic.

Interactions
------------
- Called by the `translate_diagnosis` node.
- Reads diagnosis/treatment text from the claim content (inline or AI-read).
- Returns a `DiagnosisMatch` (defined in models/decision.py).
"""

from __future__ import annotations

import re
from typing import Any

from app.models.claim import ClaimRequest
from app.models.decision import DiagnosisMatch
from app.models.policy import Policy
from app.rules.bill_details import get_document_fields


def _contains_word(text_lower: str, term: str) -> bool:
    """Whole-word match, so 'hernia' does NOT match 'herniation'."""
    return re.search(rf"\b{re.escape(term)}\b", text_lower) is not None


# Waiting-period key -> words that imply it.
_WAITING_KEYWORDS: dict[str, list[str]] = {
    "diabetes": ["diabetes", "diabetic", "t2dm", "type 2 diabetes", "type 1 diabetes"],
    "hypertension": ["hypertension", "htn", "high blood pressure"],
    "thyroid_disorders": ["thyroid", "hypothyroid", "hyperthyroid", "goiter"],
    "joint_replacement": ["joint replacement", "knee replacement", "hip replacement"],
    "maternity": ["maternity", "pregnancy", "pregnant", "delivery", "obstetric", "antenatal"],
    "mental_health": ["depression", "anxiety", "mental health", "psychiatric", "bipolar"],
    "obesity_treatment": ["obesity", "obese", "bariatric"],
    "hernia": ["hernia"],
    "cataract": ["cataract"],
}

# Words that imply a permanent exclusion.
_EXCLUSION_KEYWORDS: list[str] = [
    "obesity",
    "obese",
    "bariatric",
    "weight loss",
    "cosmetic",
    "aesthetic",
    "infertility",
    "assisted reproduction",
    "substance abuse",
    "experimental",
]


def _get_diagnosis_text(request: ClaimRequest, read_fields: dict[str, Any]) -> str:
    parts: list[str] = []
    for doc in request.documents:
        fields = get_document_fields(doc, read_fields)
        for key in ("diagnosis", "treatment"):
            value = fields.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " | ".join(parts)


def _find_excluded_condition(text_lower: str, policy: Policy) -> str | None:
    matched = [word for word in _EXCLUSION_KEYWORDS if _contains_word(text_lower, word)]
    if not matched:
        return None
    # Cite a real phrase from the policy when one mentions a matched word.
    for phrase in policy.exclusions.conditions:
        if any(word in phrase.lower() for word in matched):
            return phrase
    return policy.exclusions.conditions[0] if policy.exclusions.conditions else "Excluded condition"


def _find_waiting_condition(text_lower: str, policy: Policy) -> str | None:
    specific = policy.waiting_periods.specific_conditions
    for key, words in _WAITING_KEYWORDS.items():
        if key in specific and any(_contains_word(text_lower, w) for w in words):
            return key
    return None


def match_diagnosis(
    request: ClaimRequest, read_fields: dict[str, Any], policy: Policy
) -> DiagnosisMatch:
    text = _get_diagnosis_text(request, read_fields)
    text_lower = text.lower()
    return DiagnosisMatch(
        raw_text=text,
        waiting_condition=_find_waiting_condition(text_lower, policy),
        excluded_condition=_find_excluded_condition(text_lower, policy),
    )
