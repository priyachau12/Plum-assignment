"""Validated shape of LLM-extracted document fields.

Purpose
-------
The extraction model returns JSON; we validate it into this typed shape before
the rule engine ever sees it. Pydantic guards against hallucinated or mis-typed
fields (e.g. a `total` that isn't a number) — a validation failure becomes an
`LLMError` and the pipeline degrades gracefully rather than feeding garbage to
the rules.

`extra="allow"` keeps any additional keys the model returns (GSTIN, NABL status,
sample IDs, …) without failing validation, so we never lose extracted data.

Interactions
------------
- `llm.client.AnthropicLLMClient.extract_document` validates into this model and
  returns `model_dump()`.
- `extraction_completeness` gives the `extract` node a rough extraction-quality
  signal that feeds the composed confidence score (see `rules/engine.py`).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtractedLineItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    description: str = ""
    amount: float | None = None


class ExtractedDocument(BaseModel):
    """Typed view of one document's extracted fields. Every field is optional —
    real documents are messy and partial — but each must be the right type."""

    model_config = ConfigDict(extra="allow")

    patient_name: str | None = None
    doctor_name: str | None = None
    doctor_registration: str | None = None
    date: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medicines: list[Any] = Field(default_factory=list)
    tests_ordered: list[Any] = Field(default_factory=list)
    hospital_name: str | None = None
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    total: float | None = None


def extraction_completeness(fields: dict[str, Any]) -> float:
    """A rough extraction-quality proxy in [0, 1] for the confidence score:
    did we recover an identity, a date, and some substantive content?"""
    signals = [
        bool(fields.get("patient_name")),
        bool(fields.get("date")),
        bool(
            fields.get("diagnosis")
            or fields.get("treatment")
            or fields.get("line_items")
            or fields.get("medicines")
            or fields.get("tests_ordered")
            or fields.get("total") is not None
        ),
    ]
    return round(sum(signals) / len(signals), 2)
