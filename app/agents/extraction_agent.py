"""The extraction self-correction agent (perception layer).

Purpose
-------
Wrap the single-shot `llm.extract_document` call in a bounded plan -> act ->
observe -> decide loop:

  1. **act**     read the document (cheap model on the first attempt).
  2. **observe** score the read with `extraction_completeness`.
  3. **decide**  good enough -> converge; too weak and attempts remain ->
                 escalate to the strong model with a sharper, field-targeted
                 prompt and retry; budget exhausted -> give up (return the best
                 read so far and flag it so the node degrades).

Why it exists
-------------
Today a weak read on a hard document (handwriting, stamps, phone photos) is
accepted as-is and only lowers confidence. The agent instead *tries to recover*
before falling back to the existing degrade-and-re-upload path — fewer claims
drop to manual review, at lower cost (cheap model first, strong model only when
needed).

Boundaries
----------
- Perception only. It never decides a claim; it only changes the quality of the
  extracted fields handed to the deterministic engine.
- Fires only on the live LLM path. The injected-content path never constructs an
  agent, so the deterministic eval is untouched.

Interactions
------------
- Constructed in `app/graph/builder.py` from the loaded LLM client + settings.
- Driven by `app/graph/nodes/extract.py`, which turns the returned
  `AttemptRecord`s into trace entries and maps `gave_up` onto `degraded`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.llm.client import LLMClient, LLMError
from app.llm.prompts import EXTRACTION_RETRY_HINT
from app.models.claim import Document
from app.models.extraction import extraction_completeness

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class ExtractionAgentConfig(BaseModel):
    """Tuning for the loop, mapped from `Settings`. When `enabled` is False the
    agent makes exactly one call with the strong model — reproducing the original
    single-shot behavior."""

    enabled: bool = True
    confidence_threshold: float = 0.67
    max_attempts: int = 3
    model_fast: str = "claude-haiku-4-5-20251001"
    model_strong: str = "claude-sonnet-4-6"

    @classmethod
    def from_settings(cls, settings: Settings) -> ExtractionAgentConfig:
        return cls(
            enabled=settings.extraction_agent_enabled,
            confidence_threshold=settings.extraction_confidence_threshold,
            max_attempts=settings.extraction_max_attempts,
            model_fast=settings.llm_model_fast,
            model_strong=settings.llm_model,
        )


class AttemptRecord(BaseModel):
    """One pass of the loop — surfaced in the trace for observability."""

    attempt: int
    model: str
    succeeded: bool
    completeness: float
    note: str


class ExtractionAgentResult(BaseModel):
    """Outcome of running the loop over one document."""

    fields: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0  # final extraction completeness in [0, 1]
    gave_up: bool = False  # True -> the node degrades the claim
    attempts: list[AttemptRecord] = Field(default_factory=list)


# Human-readable buckets that mirror the three `extraction_completeness` signals.
# This is document-schema guidance (what a medical document generally carries),
# NOT policy — so it stays out of the policy-driven decision logic.
def _missing_buckets(fields: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not fields.get("patient_name"):
        missing.append("patient name")
    if not fields.get("date"):
        missing.append("date")
    has_content = any(
        fields.get(k)
        for k in ("diagnosis", "treatment", "line_items", "medicines", "tests_ordered")
    ) or fields.get("total") is not None
    if not has_content:
        missing.append("amounts or clinical details")
    return missing


class ExtractionAgent:
    """A self-correcting extraction loop over one document."""

    def __init__(self, llm: LLMClient, config: ExtractionAgentConfig) -> None:
        self._llm = llm
        self._config = config

    def run(self, document: Document) -> ExtractionAgentResult:
        cfg = self._config
        max_attempts = cfg.max_attempts if cfg.enabled else 1

        attempts: list[AttemptRecord] = []
        best_fields: dict[str, Any] = {}
        best_completeness = -1.0

        for i in range(max_attempts):
            # Tiering: cheap model only on the first try AND only when a retry is
            # actually possible (enabled, multi-attempt). A disabled or
            # single-attempt run uses the strong model directly — a lone cheap
            # shot with no chance to escalate would be strictly worse.
            use_fast = cfg.enabled and i == 0 and max_attempts > 1
            model = cfg.model_fast if use_fast else cfg.model_strong
            prompt_hint = None
            if i > 0:
                missing = _missing_buckets(best_fields) or ["key fields"]
                prompt_hint = EXTRACTION_RETRY_HINT.format(missing=", ".join(missing))

            try:
                fields = self._llm.extract_document(document, model=model, prompt_hint=prompt_hint)
            except LLMError as exc:
                attempts.append(
                    AttemptRecord(
                        attempt=i + 1,
                        model=model,
                        succeeded=False,
                        completeness=0.0,
                        note=f"extraction call failed: {exc}",
                    )
                )
                continue

            completeness = extraction_completeness(fields)
            if completeness > best_completeness:
                best_completeness, best_fields = completeness, fields

            if completeness >= cfg.confidence_threshold:
                attempts.append(
                    AttemptRecord(
                        attempt=i + 1,
                        model=model,
                        succeeded=True,
                        completeness=completeness,
                        note="converged (completeness met the threshold)",
                    )
                )
                return ExtractionAgentResult(
                    fields=fields, confidence=completeness, gave_up=False, attempts=attempts
                )

            attempts.append(
                AttemptRecord(
                    attempt=i + 1,
                    model=model,
                    succeeded=True,
                    completeness=completeness,
                    note=(
                        "below threshold; escalating"
                        if i + 1 < max_attempts
                        else "below threshold; budget exhausted"
                    ),
                )
            )

        # Never converged within budget. Hand back the best read so far (possibly
        # empty if every attempt errored) and flag it so the node degrades.
        logger.warning(
            "extraction agent gave up after %d attempt(s); best completeness %.2f",
            len(attempts),
            max(best_completeness, 0.0),
        )
        return ExtractionAgentResult(
            fields=best_fields,
            confidence=max(best_completeness, 0.0),
            gave_up=True,
            attempts=attempts,
        )
