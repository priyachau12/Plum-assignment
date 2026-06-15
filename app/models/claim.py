"""Claim submission models — the INPUT side of the system.

Purpose
-------
Type and validate exactly what a caller submits in `POST /claims`, matching the
shape used in `test_cases.json`.

Why it exists
-------------
The request is the system's trust boundary. Modeling it with Pydantic means a
malformed submission is rejected with a 422 *before* it ever reaches the graph,
and every downstream node gets typed, validated data.

Interactions
------------
- `api/routes_claims.py` declares a `ClaimRequest` parameter (FastAPI validates).
- `graph/state.py` carries the `ClaimRequest` through the pipeline.
- `verification/document_checks.py` reads documents off it.

Modeling notes
--------------
- Enums (`ClaimCategory`, `DocumentType`, `DocumentQuality`) reject unknown
  values at the edge and give the UI a fixed vocabulary.
- A document arrives one of two ways:
    (a) JSON with `actual_type` + pre-extracted `content` — the deterministic
        path the 12 test cases use; or
    (b) a real upload (image/PDF) carried as `data_base64` + `media_type` with
        `actual_type` left unset — the vision path, where `label_documents`
        classifies it and `read_documents` extracts its fields with the LLM.
  `actual_type` is therefore optional: declared by the caller, or resolved by
  vision before the document-verification gate runs.
- Optional fields (`hospital_name`, `ytd_claims_amount`, `claims_history`,
  `simulate_component_failure`) appear in only some test cases; they are modeled
  now so the request shape is stable, even though they are consumed by the rule
  engine in later phases.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClaimCategory(str, Enum):
    """The six OPD claim categories the policy covers."""

    CONSULTATION = "CONSULTATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    PHARMACY = "PHARMACY"
    DENTAL = "DENTAL"
    VISION = "VISION"
    ALTERNATIVE_MEDICINE = "ALTERNATIVE_MEDICINE"


class DocumentType(str, Enum):
    """Recognized document types (matches policy `document_requirements`)."""

    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    PHARMACY_BILL = "PHARMACY_BILL"
    LAB_REPORT = "LAB_REPORT"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DENTAL_REPORT = "DENTAL_REPORT"


class DocumentQuality(str, Enum):
    """Readability of an uploaded document. Defaults to GOOD when not provided."""

    GOOD = "GOOD"
    UNREADABLE = "UNREADABLE"


class Document(BaseModel):
    """One uploaded document plus the metadata needed to verify it.

    `actual_type` is optional: the caller may declare it (JSON path) or it is
    resolved by the vision classifier in `label_documents` for real uploads.
    `data_base64`/`media_type` carry the raw file bytes for the vision path.
    """

    file_id: str
    actual_type: DocumentType | None = None
    file_name: str | None = None
    quality: DocumentQuality = DocumentQuality.GOOD
    patient_name_on_doc: str | None = None
    content: dict[str, Any] | None = None

    # Real-upload payload (images / PDFs). Absent on the JSON/eval path.
    media_type: str | None = None  # e.g. "image/jpeg", "application/pdf"
    data_base64: str | None = None  # base64-encoded file bytes

    @property
    def has_bytes(self) -> bool:
        """True when raw file bytes are attached (the vision path applies)."""
        return bool(self.data_base64)

    def type_label(self) -> str:
        """Human/UI label for the document's type, even before classification."""
        return self.actual_type.value if self.actual_type else "UNIDENTIFIED_DOCUMENT"

    def patient_name(self) -> str | None:
        """Best-known patient name for this document: the explicit field if
        present, else the `patient_name` inside extracted `content`, else None."""
        if self.patient_name_on_doc:
            return self.patient_name_on_doc
        if self.content and isinstance(self.content.get("patient_name"), str):
            return self.content["patient_name"]
        return None


class ClaimHistoryEntry(BaseModel):
    """A prior claim, used by fraud rules in a later phase (TC009).

    The input key is `date`; we name the Python field `claim_date` (via alias)
    so it doesn't shadow the `date` type during annotation evaluation.
    """

    model_config = ConfigDict(populate_by_name=True)

    claim_id: str | None = None
    claim_date: date | None = Field(default=None, alias="date")
    amount: float | None = None
    provider: str | None = None


class ClaimRequest(BaseModel):
    """A full claim submission."""

    member_id: str
    policy_id: str
    claim_category: ClaimCategory
    treatment_date: date
    claimed_amount: float = Field(gt=0, description="Amount claimed, in INR; must be positive")
    documents: list[Document] = Field(min_length=1, description="At least one document")

    # Optional inputs used by the rule engine.
    hospital_name: str | None = None
    ytd_claims_amount: float | None = None
    claims_history: list[ClaimHistoryEntry] = Field(default_factory=list)
    pre_authorization_obtained: bool = False  # set true if member obtained pre-auth
    simulate_component_failure: bool = False  # TC011: force a node to fail
