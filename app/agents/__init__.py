"""Perception-layer agents.

Single autonomous component today: the `ExtractionAgent`, a self-correcting
document-extraction loop (read -> observe quality -> re-prompt / escalate model /
give up). It lives in the perception layer only — cognition (the rule engine)
stays deterministic. The loop is intentionally generic so a future
`ClassificationAgent` can reuse the same pattern.
"""

from __future__ import annotations

from app.agents.extraction_agent import (
    AttemptRecord,
    ExtractionAgent,
    ExtractionAgentConfig,
    ExtractionAgentResult,
)

__all__ = [
    "AttemptRecord",
    "ExtractionAgent",
    "ExtractionAgentConfig",
    "ExtractionAgentResult",
]
