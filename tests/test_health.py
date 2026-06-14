"""Tests for the /health endpoint."""

from __future__ import annotations


def test_health_reports_ok_and_policy_summary(client):
    resp = client.get("/health")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "ok"
    assert body["environment"] == "development"
    assert body["policy"]["loaded"] is True
    assert body["policy"]["policy_id"] == "PLUM_GHI_2024"
    assert body["policy"]["members"] == 12
    assert body["policy"]["categories"] == 6
