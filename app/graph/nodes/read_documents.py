"""read_documents node (AI-allowed) + graceful degradation (TC011).

Gets structured fields for each document. If a document already carries inline
content (the test cases do), use it — no AI. Otherwise, if the AI is configured,
read the fields via the model and validate them. If neither is possible, mark
the claim degraded and continue.

Failure handling
----------------
- `simulate_component_failure` (TC011): record a FAILED trace note, set
  `degraded`, and continue — the pipeline must not crash.
- AI error on a real document: trace FAILED, set `degraded`, continue.

- Bound to the (optional) `llm` client in `graph/builder.py`.
- Writes `read_fields` (file_id -> fields) and/or `degraded` + trace.
"""

from __future__ import annotations

import logging
from typing import Any

from app.graph.state import ClaimState
from app.llm.client import LLMClient, LLMError
from app.models.decision import TraceEntry, TraceStatus

logger = logging.getLogger(__name__)


def read_documents(state: ClaimState, *, llm: LLMClient | None) -> dict:
    request = state["request"]

    # TC011: a component fails mid-pipeline. We degrade, we do not crash.
    if request.simulate_component_failure:
        logger.warning("read_documents: simulated component failure")
        return {
            "degraded": True,
            "trace": [
                TraceEntry(
                    step="read_documents",
                    status=TraceStatus.FAILED,
                    detail="Simulated component failure: reading skipped. "
                    "Continuing with available data; confidence reduced.",
                    data={"degraded": True},
                )
            ],
        }

    entries: list[TraceEntry] = []
    read_fields: dict[str, dict[str, Any]] = {}
    degraded = False

    for doc in request.documents:
        if doc.content:
            entries.append(
                TraceEntry(
                    step="read_documents",
                    status=TraceStatus.OK,
                    detail=f"{doc.file_id}: used caller-provided structured content.",
                    data={"file_id": doc.file_id, "source": "provided"},
                )
            )
        elif llm is not None:  # real-document path
            try:
                read_fields[doc.file_id] = llm.read_document_fields(doc)
                entries.append(
                    TraceEntry(
                        step="read_documents",
                        status=TraceStatus.OK,
                        detail=f"{doc.file_id}: fields read by the AI.",
                        data={"file_id": doc.file_id, "source": "llm"},
                    )
                )
            except LLMError as exc:
                degraded = True
                entries.append(
                    TraceEntry(
                        step="read_documents",
                        status=TraceStatus.FAILED,
                        detail=f"{doc.file_id}: AI reading failed: {exc}",
                        data={"file_id": doc.file_id},
                    )
                )
        else:
            degraded = True
            entries.append(
                TraceEntry(
                    step="read_documents",
                    status=TraceStatus.SKIPPED,
                    detail=f"{doc.file_id}: no content and no AI configured; fields unavailable.",
                    data={"file_id": doc.file_id},
                )
            )

    update: dict = {"trace": entries}
    if read_fields:
        update["read_fields"] = read_fields
    if degraded:
        update["degraded"] = True
    return update
