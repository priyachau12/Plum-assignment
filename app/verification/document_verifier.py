"""Document verification — the deterministic early-stop gate.

Purpose
-------
Decide, before any claim decision, whether the uploaded documents are usable:
  1. are all REQUIRED document types present for the claim category?  (TC001)
  2. is every document READABLE?                                       (TC002)
  3. do all documents belong to the SAME patient?                      (TC003)

Each check is a pure function returning `(problems, trace_entry)`. All checks
run (so a claim with several problems reports all of them), and every check
writes a trace note whether it passed or failed.

Why it exists
-------------
This is the "catch document problems early" requirement. Messages must be
SPECIFIC and ACTIONABLE — naming the document type uploaded, the type required,
or the conflicting patient names — never a generic error.

Interactions
------------
- Input: a validated `ClaimRequest` + the loaded `Policy`.
- Output: a `DocumentVerificationResult` (passed flag, blocking issues, trace).
- Called by `app/graph/nodes/verify_documents.py`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.claim import ClaimRequest, Document, DocumentQuality
from app.models.decision import BlockingIssue, BlockingReason, TraceEntry, TraceStatus
from app.models.policy import Policy


class DocumentVerificationResult(BaseModel):
    """Outcome of running every document check over one claim."""

    passed: bool
    blocking_issues: list[BlockingIssue] = Field(default_factory=list)
    trace_entries: list[TraceEntry] = Field(default_factory=list)


def _clean_name(name: str) -> str:
    """Lowercase + collapse internal whitespace, so 'Rajesh  Kumar' and
    'rajesh kumar' compare equal but 'Rajesh Kumar' vs 'Arjun Mehta' do not."""
    return " ".join(name.lower().split())


def _check_required_documents_present(
    request: ClaimRequest, policy: Policy
) -> tuple[list[BlockingIssue], TraceEntry]:
    """TC001: every required document type for the category must be present."""
    requirement = policy.document_requirement(request.claim_category.value)
    if requirement is None:
        return [], TraceEntry(
            step="verify.required_documents",
            status=TraceStatus.OK,
            detail=f"No document requirements configured for {request.claim_category.value}.",
        )

    uploaded_types = [doc.type_label() for doc in request.documents]
    present = set(uploaded_types)
    missing = [t for t in requirement.required if t not in present]

    if missing:
        message = (
            f"You uploaded: {', '.join(uploaded_types)}. "
            f"A {request.claim_category.value} claim requires these document(s): "
            f"{', '.join(requirement.required)}. "
            f"The following required document(s) are missing: {', '.join(missing)}. "
            f"Please upload the missing document(s) and resubmit."
        )
        issue = BlockingIssue(
            reason=BlockingReason.MISSING_REQUIRED_DOCUMENT,
            message=message,
            details={
                "required": requirement.required,
                "uploaded": uploaded_types,
                "missing": missing,
            },
        )
        return [issue], TraceEntry(
            step="verify.required_documents",
            status=TraceStatus.BLOCKED,
            detail=message,
            data={"missing": missing, "uploaded": uploaded_types},
        )

    return [], TraceEntry(
        step="verify.required_documents",
        status=TraceStatus.OK,
        detail=f"All required documents present for {request.claim_category.value}: "
        f"{', '.join(requirement.required)}.",
        data={"uploaded": uploaded_types},
    )


def _check_readable(request: ClaimRequest) -> tuple[list[BlockingIssue], TraceEntry]:
    """TC002: any UNREADABLE document blocks the claim with a re-upload ask
    (NOT a rejection)."""
    unreadable: list[Document] = [
        doc for doc in request.documents if doc.quality == DocumentQuality.UNREADABLE
    ]

    if unreadable:
        issues: list[BlockingIssue] = []
        for doc in unreadable:
            name = doc.file_name or doc.file_id
            message = (
                f"The {doc.type_label()} ({name}) could not be read — the image "
                f"quality is too low. Please re-upload a clearer photo or scan of this "
                f"document. Your claim has NOT been rejected; we just need a readable copy."
            )
            issues.append(
                BlockingIssue(
                    reason=BlockingReason.UNREADABLE_DOCUMENT,
                    message=message,
                    details={"file_id": doc.file_id, "document_type": doc.type_label()},
                )
            )
        return issues, TraceEntry(
            step="verify.readability",
            status=TraceStatus.BLOCKED,
            detail=f"{len(unreadable)} document(s) are unreadable and must be re-uploaded.",
            data={"unreadable_file_ids": [d.file_id for d in unreadable]},
        )

    return [], TraceEntry(
        step="verify.readability",
        status=TraceStatus.OK,
        detail="All documents are readable.",
    )


def _check_same_patient(request: ClaimRequest) -> tuple[list[BlockingIssue], TraceEntry]:
    """TC003: all documents that name a patient must name the SAME patient."""
    named: list[tuple[Document, str]] = []
    for doc in request.documents:
        name = doc.patient_name()
        if name:
            named.append((doc, name.strip()))

    distinct = {_clean_name(name) for _, name in named}

    if len(distinct) > 1:
        parts = [f"the {doc.type_label()} names '{name}'" for doc, name in named]
        message = (
            "The uploaded documents appear to belong to different patients: "
            + "; ".join(parts)
            + ". All documents in a single claim must be for the same patient. "
            "Please check the documents and resubmit."
        )
        issue = BlockingIssue(
            reason=BlockingReason.PATIENT_MISMATCH,
            message=message,
            details={"names_found": {doc.type_label(): name for doc, name in named}},
        )
        return [issue], TraceEntry(
            step="verify.patient_consistency",
            status=TraceStatus.BLOCKED,
            detail=message,
            data={"distinct_names": sorted(distinct)},
        )

    only = next(iter(distinct), None)
    detail = (
        f"All documents name the same patient ('{named[0][1]}')."
        if only is not None
        else "No patient names were present on the documents to compare."
    )
    return [], TraceEntry(step="verify.patient_consistency", status=TraceStatus.OK, detail=detail)


def verify_documents(request: ClaimRequest, policy: Policy) -> DocumentVerificationResult:
    """Run all document checks and aggregate their problems + trace entries."""
    required_issues, required_trace = _check_required_documents_present(request, policy)
    readable_issues, readable_trace = _check_readable(request)
    patient_issues, patient_trace = _check_same_patient(request)

    blocking_issues = required_issues + readable_issues + patient_issues
    return DocumentVerificationResult(
        passed=not blocking_issues,
        blocking_issues=blocking_issues,
        trace_entries=[required_trace, readable_trace, patient_trace],
    )
