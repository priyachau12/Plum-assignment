"""Pipeline builder — wires the claim-processing line.

    START -> find_member -> label_documents -> check_documents -->(stop)--> END
                                                     \\
                                                      -->(continue)--> read_documents
                                                         -> translate_diagnosis
                                                         -> decide_claim -> write_explanation -> END

Why this shape
--------------
- The fork after `check_documents` is the early-stop gate: a claim with a
  document problem ends immediately with a specific message (TC001-TC003) and
  never reaches reading or the decision.
- The clean path reads the documents, translates the diagnosis, runs the
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

from app.graph.nodes.check_documents import check_documents
from app.graph.nodes.decide_claim import decide_claim
from app.graph.nodes.find_member import find_member
from app.graph.nodes.label_documents import label_documents
from app.graph.nodes.read_documents import read_documents
from app.graph.nodes.translate_diagnosis import translate_diagnosis
from app.graph.nodes.write_explanation import write_explanation
from app.graph.state import ClaimState
from app.llm.client import LLMClient
from app.models.policy import Policy

logger = logging.getLogger(__name__)


def _after_document_check(state: ClaimState) -> str:
    """The fork: a blocked claim stops; a clean one continues to reading."""
    return "stop" if state.get("blocking_issues") else "continue"


def build_graph(policy: Policy, llm: LLMClient | None = None):
    """Build and compile the full claim-processing pipeline."""
    graph = StateGraph(ClaimState)

    # Deterministic steps get the policy; AI steps get the (optional) client.
    graph.add_node("find_member", partial(find_member, policy=policy))
    graph.add_node("label_documents", partial(label_documents, llm=llm))
    graph.add_node("check_documents", partial(check_documents, policy=policy))
    graph.add_node("read_documents", partial(read_documents, llm=llm))
    graph.add_node("translate_diagnosis", partial(translate_diagnosis, policy=policy))
    graph.add_node("decide_claim", partial(decide_claim, policy=policy))
    graph.add_node("write_explanation", partial(write_explanation, llm=llm))

    graph.add_edge(START, "find_member")
    graph.add_edge("find_member", "label_documents")
    graph.add_edge("label_documents", "check_documents")
    graph.add_conditional_edges(
        "check_documents",
        _after_document_check,
        {"stop": END, "continue": "read_documents"},
    )
    graph.add_edge("read_documents", "translate_diagnosis")
    graph.add_edge("translate_diagnosis", "decide_claim")
    graph.add_edge("decide_claim", "write_explanation")
    graph.add_edge("write_explanation", END)

    compiled = graph.compile()
    logger.info(
        "Claim pipeline compiled: find_member -> label_documents -> check_documents -> "
        "{stop: END | continue: read_documents -> translate_diagnosis -> decide_claim "
        "-> write_explanation -> END}"
    )
    return compiled
