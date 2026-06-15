"""classify node (AI-allowed) — the classification pass.

Decides what type each document is, whether it is readable, and whose name is on
it. When the caller already declared the type (as the 12 test cases do), we trust
it. For a real upload (image/PDF bytes, no declared type) the vision model runs
and we resolve the findings ONTO the document, so the downstream
document-verification gate (`verify_documents`) can catch the wrong type, an
unreadable scan, or a patient mismatch on real documents — before any extraction.

Why resolve onto the document
-----------------------------
`verify_documents`, `extract`, and the rule engine all read `actual_type`,
`quality`, and the patient name straight off each `Document`. Writing the vision
findings back there keeps every later step unchanged whether the type was
declared or classified.

- Bound to the (optional) `llm` client in `graph/builder.py`.
- Writes `classified_docs` (file_id -> resolved type) + trace.
"""

from __future__ import annotations

import logging

from app.graph.state import ClaimState
from app.llm.client import LLMClient, LLMError
from app.models.claim import DocumentQuality, DocumentType
from app.models.decision import TraceEntry, TraceStatus

logger = logging.getLogger(__name__)


def _coerce_type(label: str | None) -> DocumentType | None:
    """Map a free-text vision label onto the DocumentType vocabulary, or None."""
    if not label:
        return None
    try:
        return DocumentType(label.strip().upper())
    except ValueError:
        return None


def classify(state: ClaimState, *, llm: LLMClient | None) -> dict:
    request = state["request"]
    classified_docs: dict[str, str] = {}
    entries: list[TraceEntry] = []

    for doc in request.documents:
        # (a) Caller declared the type (JSON / eval path): trust it.
        if doc.actual_type is not None:
            classified_docs[doc.file_id] = doc.actual_type.value
            entries.append(
                TraceEntry(
                    step="classify",
                    status=TraceStatus.OK,
                    detail=f"{doc.file_id}: type {doc.actual_type.value} (declared by caller).",
                    data={
                        "file_id": doc.file_id,
                        "type": doc.actual_type.value,
                        "source": "declared",
                    },
                )
            )
            continue

        # (b) Real upload, no declared type: classify with vision.
        if llm is not None:
            try:
                classification = llm.classify_document(doc)
            except LLMError as exc:
                entries.append(
                    TraceEntry(
                        step="classify",
                        status=TraceStatus.FAILED,
                        detail=f"{doc.file_id}: could not classify document: {exc}",
                        data={"file_id": doc.file_id},
                    )
                )
                continue

            resolved = _coerce_type(classification.document_type)
            if resolved is not None:
                doc.actual_type = resolved
                classified_docs[doc.file_id] = resolved.value
            if not classification.readable:
                doc.quality = DocumentQuality.UNREADABLE
            if classification.patient_name and not doc.patient_name_on_doc:
                doc.patient_name_on_doc = classification.patient_name

            status = TraceStatus.OK if resolved is not None else TraceStatus.FAILED
            detail = (
                f"{doc.file_id}: identified as {resolved.value} by the AI"
                if resolved is not None
                else f"{doc.file_id}: AI could not identify the document type"
            )
            patient = classification.patient_name
            patient_note = f", patient={patient}" if patient else ""
            entries.append(
                TraceEntry(
                    step="classify",
                    status=status,
                    detail=f"{detail} (readable={classification.readable}{patient_note}).",
                    data={
                        "file_id": doc.file_id,
                        "type": resolved.value if resolved else None,
                        "readable": classification.readable,
                        "patient_name": classification.patient_name,
                        "source": "llm",
                    },
                )
            )
            continue

        # (c) No declared type and no AI configured: cannot classify.
        entries.append(
            TraceEntry(
                step="classify",
                status=TraceStatus.SKIPPED,
                detail=f"{doc.file_id}: no declared type and no AI configured; type unidentified.",
                data={"file_id": doc.file_id},
            )
        )

    return {"classified_docs": classified_docs, "trace": entries}
