"""Tests for the claim request models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.claim import ClaimCategory, ClaimRequest, DocumentType
from tests.helpers import case_input, claim_request


def test_parses_tc004_input():
    req = claim_request("TC004")
    assert req.member_id == "EMP001"
    assert req.claim_category == ClaimCategory.CONSULTATION
    assert len(req.documents) == 2
    assert req.documents[0].actual_type == DocumentType.PRESCRIPTION
    # patient name pulled from extracted content
    assert req.documents[0].patient_name() == "Rajesh Kumar"


def test_patient_name_uses_explicit_field_when_present():
    req = claim_request("TC003")
    names = {doc.patient_name() for doc in req.documents}
    assert "Rajesh Kumar" in names
    assert "Arjun Mehta" in names


def test_rejects_non_positive_amount():
    data = dict(case_input("TC004"))
    data["claimed_amount"] = 0
    with pytest.raises(ValidationError):
        ClaimRequest(**data)


def test_rejects_empty_documents():
    data = dict(case_input("TC004"))
    data["documents"] = []
    with pytest.raises(ValidationError):
        ClaimRequest(**data)


def test_rejects_unknown_category():
    data = dict(case_input("TC004"))
    data["claim_category"] = "SPA_DAY"
    with pytest.raises(ValidationError):
        ClaimRequest(**data)
