"""Tests for the AI-using steps, with a FAKE client (no network).

Proves the AI seam works: reading uses validated model output, falls back /
degrades on failure, and explanation prefers the AI but keeps the built text
when the model fails.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.graph.nodes.read_documents import read_documents
from app.graph.nodes.write_explanation import write_explanation
from app.llm.client import LLMClient, LLMError
from app.models.claim import ClaimRequest, Document
from app.models.decision import Decision, DecisionResult, TraceStatus


class FakeLLM(LLMClient):
    def __init__(
        self, fields: dict | None = None, explanation: str = "AI TEXT", fail: bool = False
    ):
        self._fields = fields or {"diagnosis": "Viral Fever"}
        self._explanation = explanation
        self._fail = fail

    def identify_document_type(self, document: Document) -> str:
        return "PRESCRIPTION"

    def read_document_fields(self, document: Document) -> dict[str, Any]:
        if self._fail:
            raise LLMError("simulated reading failure")
        return self._fields

    def write_explanation(self, decision, approved_amount, reasons, fallback) -> str:
        if self._fail:
            raise LLMError("simulated explanation failure")
        return self._explanation


def _request_without_content() -> ClaimRequest:
    return ClaimRequest(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category="CONSULTATION",
        treatment_date="2024-11-01",
        claimed_amount=1500,
        documents=[Document(file_id="F1", actual_type="PRESCRIPTION")],  # no inline content
    )


def test_read_documents_uses_validated_ai_output():
    out = read_documents(
        {"request": _request_without_content()}, llm=FakeLLM(fields={"diagnosis": "Dengue"})
    )
    assert out["read_fields"]["F1"]["diagnosis"] == "Dengue"
    assert not out.get("degraded")


def test_read_documents_degrades_on_ai_error():
    out = read_documents({"request": _request_without_content()}, llm=FakeLLM(fail=True))
    assert out["degraded"] is True
    assert any(t.status == TraceStatus.FAILED for t in out["trace"])


def test_read_documents_degrades_without_ai():
    out = read_documents({"request": _request_without_content()}, llm=None)
    assert out["degraded"] is True
    assert any(t.status == TraceStatus.SKIPPED for t in out["trace"])


@pytest.fixture
def approved_result() -> DecisionResult:
    return DecisionResult(
        decision=Decision.APPROVED,
        approved_amount=1350,
        confidence=0.95,
        financial_breakdown={
            "is_network": False,
            "covered_base": 1500,
            "network_discount_percent": 0,
            "after_network_discount": 1500,
            "copay_percent": 10,
            "after_copay": 1350,
        },
    )


def test_write_explanation_prefers_ai(approved_result):
    out = write_explanation(
        {"decision_details": approved_result}, llm=FakeLLM(explanation="Friendly text")
    )
    assert out["explanation"] == "Friendly text"


def test_write_explanation_falls_back_to_built_text_on_failure(approved_result):
    out = write_explanation({"decision_details": approved_result}, llm=FakeLLM(fail=True))
    assert "1350" in out["explanation"]  # deterministic built text still works
