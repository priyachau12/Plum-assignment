"""Tests for the pipeline wiring — the early-stop fork and the full clean path."""

from __future__ import annotations

from app.graph.builder import build_graph
from tests.helpers import claim_request


def test_clean_claim_runs_full_pipeline(policy):
    pipeline = build_graph(policy, llm=None)
    state = pipeline.invoke({"claim_id": "T1", "request": claim_request("TC004")})
    steps = [entry.step for entry in state["trace"]]
    assert "find_member" in steps
    assert "label_documents" in steps
    assert "check.required_documents" in steps
    assert "decide.money_math" in steps
    assert "write_explanation" in steps
    assert not state.get("blocking_issues")
    assert state["status"].value == "DECIDED"


def test_blocked_claim_skips_decision(policy):
    pipeline = build_graph(policy, llm=None)
    state = pipeline.invoke({"claim_id": "T2", "request": claim_request("TC001")})
    steps = [entry.step for entry in state["trace"]]
    assert "find_member" in steps
    # The fork must route a blocked claim straight to END.
    assert not any(s.startswith("decide") for s in steps)
    assert "write_explanation" not in steps
    assert state["blocking_issues"]
    assert state["status"].value == "BLOCKED"
