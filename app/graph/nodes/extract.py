"""extract node (AI-allowed) + graceful degradation (TC011).

Gets structured fields for each document. If a document already carries inline
content (the test cases do), use it — no AI, deterministic. Otherwise, if an
extraction agent is configured, run its self-correction loop (retry + model
escalation) and use its best read. If neither is possible, mark the claim
degraded and continue.

Failure handling
----------------
- `simulate_component_failure` (TC011): record a FAILED trace note, set
  `degraded`, and continue — the pipeline must not crash.
- Agent gave up (budget exhausted, still weak, or every call errored): trace the
  attempts, set `degraded`, keep any best-effort fields, continue.

- Bound to the (optional) `ExtractionAgent` in `graph/builder.py`.
- Writes `extracted_content` (file_id -> fields), `extraction_confidence`,
  and/or `degraded` + trace.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.extraction_agent import ExtractionAgent
from app.graph.state import ClaimState
from app.models.decision import TraceEntry, TraceStatus

logger = logging.getLogger(__name__)


def extract(state: ClaimState, *, agent: ExtractionAgent | None) -> dict:
    request = state["request"]

    # TC011: a component fails mid-pipeline. We degrade, we do not crash.
    if request.simulate_component_failure:
        logger.warning("extract: simulated component failure")
        return {
            "degraded": True,
            "trace": [
                TraceEntry(
                    step="extract",
                    status=TraceStatus.FAILED,
                    detail="Simulated component failure: extraction skipped. "
                    "Continuing with available data; confidence reduced.",
                    data={"degraded": True},
                )
            ],
        }

    entries: list[TraceEntry] = []
    extracted_content: dict[str, dict[str, Any]] = {}
    degraded = False
    confidences: list[float] = []  # per-document extraction-quality on the agent path

    for doc in request.documents:
        if doc.content:
            # Deterministic path: caller-provided content. The agent never runs
            # here, which is what keeps the injected-content eval reproducible.
            entries.append(
                TraceEntry(
                    step="extract",
                    status=TraceStatus.OK,
                    detail=f"{doc.file_id}: used caller-provided structured content.",
                    data={"file_id": doc.file_id, "source": "provided"},
                )
            )
        elif agent is not None:  # real-document path — the self-correction loop
            result = agent.run(doc)
            for rec in result.attempts:
                entries.append(
                    TraceEntry(
                        step="extract",
                        status=TraceStatus.OK if rec.succeeded else TraceStatus.FAILED,
                        detail=(
                            f"{doc.file_id}: attempt {rec.attempt} [{rec.model}] {rec.note} "
                            f"(completeness {rec.completeness:.2f})."
                        ),
                        data={
                            "file_id": doc.file_id,
                            "attempt": rec.attempt,
                            "model": rec.model,
                            "completeness": rec.completeness,
                            "source": "agent",
                        },
                    )
                )

            if result.fields:
                extracted_content[doc.file_id] = result.fields
                confidences.append(result.confidence)

            if result.gave_up:
                degraded = True
                entries.append(
                    TraceEntry(
                        step="extract",
                        status=TraceStatus.FAILED,
                        detail=(
                            f"{doc.file_id}: extraction did not reach confidence after "
                            f"{len(result.attempts)} attempt(s); continuing with partial data. "
                            "A clearer copy of this document is recommended."
                        ),
                        data={"file_id": doc.file_id, "gave_up": True},
                    )
                )
            else:
                entries.append(
                    TraceEntry(
                        step="extract",
                        status=TraceStatus.OK,
                        detail=(
                            f"{doc.file_id}: fields extracted by the agent "
                            f"(completeness {result.confidence:.2f}) in {len(result.attempts)} "
                            "attempt(s)."
                        ),
                        data={"file_id": doc.file_id, "source": "agent"},
                    )
                )
        else:
            degraded = True
            entries.append(
                TraceEntry(
                    step="extract",
                    status=TraceStatus.SKIPPED,
                    detail=f"{doc.file_id}: no content and no AI configured; fields unavailable.",
                    data={"file_id": doc.file_id},
                )
            )

    update: dict = {"trace": entries}
    if extracted_content:
        update["extracted_content"] = extracted_content
    if confidences:
        # Average extraction quality across agent-read documents; feeds the
        # composed confidence score. (Unset on the inject-content path, where the
        # caller-provided content is trusted, so confidence stays at its base.)
        update["extraction_confidence"] = round(sum(confidences) / len(confidences), 2)
    if degraded:
        update["degraded"] = True
    return update
