"""Pipeline builder — wires the claim-processing line.

    START -> intake -> classify -> verify_documents -->(stop)--> END
                                            \\
                                             -->(continue)--> extract
                                                -> normalize_diagnosis
                                                -> adjudicate -> explain -> END

Why this shape
--------------
- The fork after `verify_documents` is the early-stop gate: a claim with a
  document problem ends immediately with a specific message (TC001-TC003) and
  never reaches extraction or the decision.
- The clean path extracts the documents, normalizes the diagnosis, runs the
  deterministic decision rules, and writes the explanation.

Dependency binding
-------------------
`policy` (loaded once) is bound into the deterministic steps and `llm` (optional)
into the AI steps via `functools.partial`, keeping each step's signature
`(state) -> dict` while giving it what it needs.

- `main.py` calls `build_graph(policy, llm)` once at startup -> `app.state.graph`.
"""

from __future__ import annotations

import logging
from functools import partial

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.adjudicate import adjudicate
from app.graph.nodes.classify import classify
from app.graph.nodes.explain import explain
from app.graph.nodes.extract import extract
from app.graph.nodes.intake import intake
from app.graph.nodes.normalize_diagnosis import normalize_diagnosis
from app.graph.nodes.verify_documents import verify_documents
from app.graph.state import ClaimState
from app.llm.client import LLMClient
from app.models.policy import Policy

logger = logging.getLogger(__name__)


def _after_document_verification(state: ClaimState) -> str:
    """The fork: a blocked claim stops; a clean one continues to extraction."""
    return "stop" if state.get("blocking_issues") else "continue"


def build_graph(policy: Policy, llm: LLMClient | None = None):
    """Build and compile the full claim-processing pipeline."""
    graph = StateGraph(ClaimState)

    # Deterministic steps get the policy; AI steps get the (optional) client.
    graph.add_node("intake", partial(intake, policy=policy))
    graph.add_node("classify", partial(classify, llm=llm))
    graph.add_node("verify_documents", partial(verify_documents, policy=policy))
    graph.add_node("extract", partial(extract, llm=llm))
    graph.add_node("normalize_diagnosis", partial(normalize_diagnosis, policy=policy))
    graph.add_node("adjudicate", partial(adjudicate, policy=policy))
    graph.add_node("explain", partial(explain, llm=llm))

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "classify")
    graph.add_edge("classify", "verify_documents")
    graph.add_conditional_edges(
        "verify_documents",
        _after_document_verification,
        {"stop": END, "continue": "extract"},
    )
    graph.add_edge("extract", "normalize_diagnosis")
    graph.add_edge("normalize_diagnosis", "adjudicate")
    graph.add_edge("adjudicate", "explain")
    graph.add_edge("explain", END)

    compiled = graph.compile()
    logger.info(
        "Claim pipeline compiled: intake -> classify -> verify_documents -> "
        "{stop: END | continue: extract -> normalize_diagnosis -> adjudicate "
        "-> explain -> END}"
    )
    return compiled
