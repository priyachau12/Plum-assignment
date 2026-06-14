"""label_documents node (AI-allowed).

Decides what type each document is. When the caller already declared the type
(as the test cases do), we trust it and record it. Only when a type is unknown
would the vision model run — that's the AI path.

- Bound to the (optional) `llm` client in `graph/builder.py`.
- Writes `document_types` (file_id -> type) + trace.
"""

from __future__ import annotations

import logging

from app.graph.state import ClaimState
from app.llm.client import LLMClient, LLMError
from app.models.decision import TraceEntry, TraceStatus

logger = logging.getLogger(__name__)


def label_documents(state: ClaimState, *, llm: LLMClient | None) -> dict:
    request = state["request"]
    document_types: dict[str, str] = {}
    entries: list[TraceEntry] = []

    for doc in request.documents:
        if doc.actual_type is not None:
            document_types[doc.file_id] = doc.actual_type.value
            entries.append(
                TraceEntry(
                    step="label_documents",
                    status=TraceStatus.OK,
                    detail=f"{doc.file_id}: type {doc.actual_type.value} (declared by caller).",
                    data={
                        "file_id": doc.file_id,
                        "type": doc.actual_type.value,
                        "source": "declared",
                    },
                )
            )
        elif llm is not None:  # real-document path
            try:
                label = llm.identify_document_type(doc)
                document_types[doc.file_id] = label
                entries.append(
                    TraceEntry(
                        step="label_documents",
                        status=TraceStatus.OK,
                        detail=f"{doc.file_id}: identified as {label} by the AI.",
                        data={"file_id": doc.file_id, "type": label, "source": "llm"},
                    )
                )
            except LLMError as exc:
                entries.append(
                    TraceEntry(
                        step="label_documents",
                        status=TraceStatus.FAILED,
                        detail=f"{doc.file_id}: could not identify type: {exc}",
                        data={"file_id": doc.file_id},
                    )
                )

    return {"document_types": document_types, "trace": entries}
