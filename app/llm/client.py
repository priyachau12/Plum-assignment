"""LLM client interface + Anthropic implementation + factory.

Purpose
-------
Define a small, injectable interface (`LLMClient`) for the three LLM tasks, plus
a concrete `AnthropicLLMClient` that uses Claude's **vision** API to read real
uploaded images/PDFs. `build_llm_client(settings)` returns a client when the LLM
is enabled and configured, else `None` (offline/deterministic).

The three tasks
---------------
- `classify_document`  : classify the document type, judge readability, and read
                         the patient name — the cheap pass that feeds the early
                         document-verification gate (so a bad-document claim stops
                         BEFORE the expensive full extraction runs).
- `extract_document`   : full structured extraction from the document.
- `generate_explanation` : member-facing rephrasing of the decision.

Why an interface
----------------
Nodes depend on the interface, not on Anthropic. Tests pass a fake client, so
the LLM-handling paths are tested without any network call or API key.

Vision
------
When a document carries raw bytes (`data_base64` + `media_type`), the prompt is
sent alongside an image or PDF content block, so Claude actually *reads the
document* — handwritten prescriptions, stamped bills, phone photos. When no
bytes are present we fall back to a filename-only prompt (best effort).

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

from pydantic import BaseModel

from app.config import Settings
from app.exceptions import ClaimsSystemError
from app.llm.prompts import CLASSIFICATION_PROMPT, EXPLANATION_PROMPT, EXTRACTION_PROMPT
from app.models.claim import Document

logger = logging.getLogger(__name__)

_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class LLMError(ClaimsSystemError):
    """Any failure calling or parsing an LLM response."""


class DocumentClassification(BaseModel):
    """Lightweight, validated result of the classification pass.

    `document_type` is the model's free-text guess; `classify` maps it onto the
    `DocumentType` vocabulary (an unmappable guess is treated as unidentified).
    `readable` drives the unreadable-document gate; `patient_name` feeds the
    same-patient gate.
    """

    document_type: str | None = None
    readable: bool = True
    patient_name: str | None = None


class LLMClient(ABC):
    """The three LLM tasks the system is allowed to use."""

    @abstractmethod
    def classify_document(self, document: Document) -> DocumentClassification: ...

    @abstractmethod
    def extract_document(self, document: Document) -> dict[str, Any]: ...

    @abstractmethod
    def generate_explanation(
        self, decision: str, approved_amount: float, reasons: list[str], fallback: str
    ) -> str: ...


class AnthropicLLMClient(LLMClient):
    """Calls Anthropic's Messages API with vision. Used on the real-document
    path (not in tests). Validates that structured tasks return JSON."""

    def __init__(self, model: str, api_key: str, timeout: float) -> None:
        try:
            import anthropic  # imported lazily so the package is optional
        except ImportError as exc:  # pragma: no cover - only without the dep
            raise LLMError("anthropic package is not installed") from exc
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self._model = model

    # --- low-level helpers ---------------------------------------------------

    def _document_block(self, document: Document) -> dict[str, Any] | None:
        """Build an image/PDF content block from the document's bytes, or None
        when no bytes are attached (filename-only fallback)."""
        if not document.data_base64:
            return None
        media_type = (document.media_type or "").lower()
        if media_type == "application/pdf":
            return {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": document.data_base64,
                },
            }
        if media_type in _SUPPORTED_IMAGE_TYPES:
            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": document.data_base64,
                },
            }
        # Unknown/declared media type with bytes: default to JPEG (most phone photos).
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": document.data_base64},
        }

    def _ask(self, document: Document, prompt: str, max_tokens: int = 1024) -> str:
        """Send the prompt, attaching the document image/PDF when available."""
        content: list[dict[str, Any]] = []
        block = self._document_block(document)
        if block is not None:
            content.append(block)
        content.append({"type": "text", "text": prompt})
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": content}],
            )
            return message.content[0].text
        except Exception as exc:  # noqa: BLE001 - normalize every provider error
            raise LLMError(f"LLM request failed: {exc}") from exc

    @staticmethod
    def _parse_json_object(raw: str, what: str) -> dict[str, Any]:
        """Parse a JSON object out of a model reply, tolerating ```json fences."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[4:] if text.lower().startswith("json") else text
            text = text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM {what} did not return valid JSON") from exc
        if not isinstance(data, dict):
            raise LLMError(f"LLM {what} JSON was not an object")
        return data

    # --- the three tasks -----------------------------------------------------

    def classify_document(self, document: Document) -> DocumentClassification:
        raw = self._ask(
            document,
            CLASSIFICATION_PROMPT.format(file_name=document.file_name or document.file_id),
            max_tokens=256,
        )
        data = self._parse_json_object(raw, "classification")
        raw_readable = data.get("readable", True)
        readable = (
            raw_readable if isinstance(raw_readable, bool) else str(raw_readable).lower() != "false"
        )
        return DocumentClassification(
            document_type=(data.get("document_type") or None),
            readable=readable,
            patient_name=(data.get("patient_name") or None),
        )

    def extract_document(self, document: Document) -> dict[str, Any]:
        raw = self._ask(
            document,
            EXTRACTION_PROMPT.format(
                document_type=document.type_label(),
                file_name=document.file_name or document.file_id,
            ),
        )
        return self._parse_json_object(raw, "extraction")

    def generate_explanation(
        self, decision: str, approved_amount: float, reasons: list[str], fallback: str
    ) -> str:
        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": EXPLANATION_PROMPT.format(
                            decision=decision,
                            approved_amount=approved_amount,
                            reasons=", ".join(reasons) or "none",
                            fallback=fallback,
                        ),
                    }
                ],
            )
            return message.content[0].text.strip()
        except Exception as exc:  # noqa: BLE001 - normalize every provider error
            raise LLMError(f"LLM request failed: {exc}") from exc


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
