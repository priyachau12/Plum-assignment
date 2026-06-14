"""End-to-end tests for POST /claims (blocking gate + decisions)."""

from __future__ import annotations

from tests.helpers import case_input


def _post(client, case_id: str):
    return client.post("/claims", json=case_input(case_id))


def test_tc001_blocks_with_missing_document(client):
    resp = _post(client, "TC001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "BLOCKED"
    assert body["decision"] is None
    reasons = {i["reason"] for i in body["blocking_issues"]}
    assert "MISSING_REQUIRED_DOCUMENT" in reasons
    assert any(t["step"] == "find_member" for t in body["trace"])


def test_tc002_blocks_with_unreadable_document(client):
    body = _post(client, "TC002").json()
    assert body["status"] == "BLOCKED"
    assert any(i["reason"] == "UNREADABLE_DOCUMENT" for i in body["blocking_issues"])


def test_tc003_blocks_with_patient_mismatch(client):
    body = _post(client, "TC003").json()
    assert body["status"] == "BLOCKED"
    assert any(i["reason"] == "PATIENT_MISMATCH" for i in body["blocking_issues"])


def test_tc004_approved_with_copay(client):
    body = _post(client, "TC004").json()
    assert body["status"] == "DECIDED"
    assert body["decision"] == "APPROVED"
    assert body["approved_amount"] == 1350
    assert body["confidence"] > 0.85
    assert body["explanation"]


def test_malformed_request_returns_422(client):
    resp = client.post("/claims", json={"member_id": "EMP001"})
    assert resp.status_code == 422
