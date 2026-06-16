"""Tests for the extraction self-correction agent (no network).

A scripted fake client returns a queued sequence of reads (dicts) or raises,
and records the model used on each call, so escalation and give-up are asserted
deterministically.
"""

from __future__ import annotations

from typing import Any

from app.agents.extraction_agent import ExtractionAgent, ExtractionAgentConfig
from app.llm.client import DocumentClassification, LLMClient, LLMError
from app.models.claim import Document

FULL = {"patient_name": "Rajesh Kumar", "date": "2024-11-01", "diagnosis": "Viral Fever"}
WEAK = {"diagnosis": "X"}  # only the content signal -> completeness 0.33

FAST = "fast-model"
STRONG = "strong-model"


class ScriptedLLM(LLMClient):
    """Returns queued responses in order; the last entry repeats if exhausted.
    Each entry is either a fields dict or an Exception instance to raise."""

    def __init__(self, responses: list[Any]):
        self._responses = responses
        self.calls: list[dict] = []  # records {model, prompt_hint} per call

    def classify_document(self, document: Document) -> DocumentClassification:
        raise NotImplementedError

    def extract_document(self, document, *, model=None, prompt_hint=None) -> dict[str, Any]:
        self.calls.append({"model": model, "prompt_hint": prompt_hint})
        resp = self._responses[min(len(self.calls) - 1, len(self._responses) - 1)]
        if isinstance(resp, Exception):
            raise resp
        return resp

    def generate_explanation(self, decision, approved_amount, reasons, fallback) -> str:
        raise NotImplementedError


def _config(**overrides) -> ExtractionAgentConfig:
    base = dict(
        enabled=True,
        confidence_threshold=0.67,
        max_attempts=3,
        model_fast=FAST,
        model_strong=STRONG,
    )
    base.update(overrides)
    return ExtractionAgentConfig(**base)


def _doc() -> Document:
    return Document(file_id="F1", actual_type="HOSPITAL_BILL")


def test_converges_on_first_read():
    llm = ScriptedLLM([FULL])
    result = ExtractionAgent(llm, _config()).run(_doc())
    assert result.gave_up is False
    assert result.confidence == 1.0
    assert len(llm.calls) == 1
    assert llm.calls[0]["model"] == FAST  # cheap model first
    assert llm.calls[0]["prompt_hint"] is None


def test_escalates_then_converges():
    llm = ScriptedLLM([WEAK, FULL])
    result = ExtractionAgent(llm, _config()).run(_doc())
    assert result.gave_up is False
    assert result.confidence == 1.0
    assert len(llm.calls) == 2
    assert llm.calls[0]["model"] == FAST
    assert llm.calls[1]["model"] == STRONG  # escalated to the strong model
    assert llm.calls[1]["prompt_hint"] is not None  # sharper retry prompt
    assert "date" in llm.calls[1]["prompt_hint"]  # names the missing buckets


def test_gives_up_when_all_reads_stay_weak():
    llm = ScriptedLLM([WEAK, WEAK, WEAK])
    result = ExtractionAgent(llm, _config()).run(_doc())
    assert result.gave_up is True
    assert len(llm.calls) == 3  # exhausted the budget
    assert result.fields == WEAK  # best-so-far partial data is still returned
    assert result.confidence == round(1 / 3, 2)


def test_recovers_after_a_failed_attempt():
    llm = ScriptedLLM([LLMError("boom"), FULL])
    result = ExtractionAgent(llm, _config()).run(_doc())
    assert result.gave_up is False
    assert result.confidence == 1.0
    assert result.attempts[0].succeeded is False
    assert result.attempts[1].succeeded is True


def test_gives_up_without_crashing_when_all_attempts_error():
    llm = ScriptedLLM([LLMError("a"), LLMError("b"), LLMError("c")])
    result = ExtractionAgent(llm, _config()).run(_doc())
    assert result.gave_up is True
    assert result.fields == {}
    assert result.confidence == 0.0
    assert all(not a.succeeded for a in result.attempts)


def test_disabled_does_single_strong_shot():
    # Disabled: exactly one call with the strong model, no escalation, even
    # though max_attempts is 3 and the read is weak.
    llm = ScriptedLLM([WEAK, FULL, FULL])
    result = ExtractionAgent(llm, _config(enabled=False)).run(_doc())
    assert len(llm.calls) == 1
    assert llm.calls[0]["model"] == STRONG
    assert llm.calls[0]["prompt_hint"] is None
    assert result.gave_up is True  # single weak shot still degrades


def test_from_settings_maps_tiers():
    from app.config import Settings

    cfg = ExtractionAgentConfig.from_settings(Settings())
    assert cfg.model_strong == Settings().llm_model  # strong tier == existing model
    assert cfg.model_fast == Settings().llm_model_fast
    assert cfg.model_fast != cfg.model_strong
