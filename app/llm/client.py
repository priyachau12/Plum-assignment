"""LLM client interface + Anthropic implementation + factory.

Purpose
-------
Define a small, injectable interface (`LLMClient`) for the three LLM tasks, plus
a concrete `AnthropicLLMClient`. `build_llm_client(settings)` returns a client
when the LLM is enabled and configured, else `None` (offline/deterministic).

Why an interface
----------------
Nodes depend on the interface, not on Anthropic. Tests pass a fake client, so
the LLM-handling paths are tested without any network call or API key.

Failure model
-------------
Every method raises `LLMError` on any provider/parse failure. Nodes catch it and
degrade gracefully (lower confidence, trace the failure) — they never crash.

Interactions
------------
- `build_llm_client` is called once in `main.lifespan`; the result is bound into
  the classify/extract/explain nodes by `graph/builder.py`.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from app.config import Settings
from app.exceptions import ClaimsSystemError
from app.llm.prompts import CLASSIFICATION_PROMPT, EXPLANATION_PROMPT, EXTRACTION_PROMPT
from app.models.claim import Document

logger = logging.getLogger(__name__)


class LLMError(ClaimsSystemError):
    """Any failure calling or parsing an LLM response."""


class LLMClient(ABC):
    """The three LLM tasks the system is allowed to use."""

    @abstractmethod
    def identify_document_type(self, document: Document) -> str: ...

    @abstractmethod
    def read_document_fields(self, document: Document) -> dict[str, Any]: ...

    @abstractmethod
    def write_explanation(
        self, decision: str, approved_amount: float, reasons: list[str], fallback: str
    ) -> str: ...


class AnthropicLLMClient(LLMClient):
    """Calls Anthropic's Messages API. Used on the real-document path (not in
    tests). Validates that extraction returns JSON."""

    def __init__(self, model: str, api_key: str, timeout: float) -> None:
        try:
            import anthropic  # imported lazily so the package is optional
        except ImportError as exc:  # pragma: no cover - only without the dep
            raise LLMError("anthropic package is not installed") from exc
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self._model = model

    def _send_prompt(self, prompt: str, max_tokens: int = 1024) -> str:
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as exc:  # noqa: BLE001 - normalize every provider error
            raise LLMError(f"LLM request failed: {exc}") from exc

    def identify_document_type(self, document: Document) -> str:
        return self._send_prompt(
            CLASSIFICATION_PROMPT.format(file_name=document.file_name or document.file_id),
            max_tokens=16,
        ).strip()

    def read_document_fields(self, document: Document) -> dict[str, Any]:
        raw = self._send_prompt(
            EXTRACTION_PROMPT.format(
                document_type=document.actual_type.value,
                file_name=document.file_name or document.file_id,
            )
        )
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError("LLM extraction did not return valid JSON") from exc
        if not isinstance(data, dict):
            raise LLMError("LLM extraction JSON was not an object")
        return data

    def write_explanation(
        self, decision: str, approved_amount: float, reasons: list[str], fallback: str
    ) -> str:
        return self._send_prompt(
            EXPLANATION_PROMPT.format(
                decision=decision,
                approved_amount=approved_amount,
                reasons=", ".join(reasons) or "none",
                fallback=fallback,
            )
        ).strip()


def build_llm_client(settings: Settings) -> LLMClient | None:
    """Return a client if the LLM is enabled + configured, else None."""
    if not settings.use_llm or not settings.anthropic_api_key:
        logger.info("LLM disabled or no API key; running with deterministic fallbacks.")
        return None
    try:
        return AnthropicLLMClient(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            timeout=settings.llm_timeout_seconds,
        )
    except LLMError as exc:
        logger.warning("Could not build LLM client (%s); using deterministic fallbacks.", exc)
        return None
