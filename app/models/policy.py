"""Pydantic models for the policy configuration (`policy_terms.json`).

Purpose
-------
Turn the raw policy JSON into typed, validated Python objects, and provide a
few normalized lookups the rule engine will rely on.

Why it exists
-------------
The assignment forbids hardcoding policy logic — rules must be *read from the
file*. Modeling the file with Pydantic means:
  - the structure is validated at load time (a malformed policy fails loudly),
  - the rest of the codebase gets autocomplete + type safety instead of dict
    spelunking,
  - the awkward casing/shape differences in the file are absorbed here, once.

Interactions
------------
- `policy/policy_loader.py` builds a `Policy` via `Policy.model_validate(...)`.
- `main.py` stores the resulting `Policy` on `app.state.policy`.
- The rule engine (later phase) reads coverage/waiting/exclusion/etc. off it.

Design note on shapes
----------------------
`opd_categories` entries differ by category (dental has procedures, diagnostic
has a pre-auth threshold, pharmacy has branded-drug co-pay...). We model ONE
`OpdCategory` with the union of fields, making category-specific ones optional.
This is simpler and more explainable than six near-identical models, at the
cost of a few always-None fields per category.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PolicyHolder(BaseModel):
    company_name: str
    employee_count: int
    policy_start_date: date
    policy_end_date: date
    renewal_status: str


class FamilyFloater(BaseModel):
    enabled: bool
    combined_limit: float
    covered_relationships: list[str]


class Coverage(BaseModel):
    sum_insured_per_employee: float
    annual_opd_limit: float
    per_claim_limit: float
    family_floater: FamilyFloater


class OpdCategory(BaseModel):
    """One coverage category. Common fields are required; category-specific
    fields are optional so a single model covers all six categories."""

    sub_limit: float
    copay_percent: float = 0
    network_discount_percent: float = 0
    requires_prescription: bool = False
    requires_pre_auth: bool = False
    covered: bool = True

    # diagnostic-specific
    pre_auth_threshold: float | None = None
    high_value_tests_requiring_pre_auth: list[str] = Field(default_factory=list)

    # pharmacy-specific
    branded_drug_copay_percent: float | None = None
    generic_mandatory: bool | None = None

    # dental-specific
    requires_dental_report: bool | None = None
    covered_procedures: list[str] = Field(default_factory=list)
    excluded_procedures: list[str] = Field(default_factory=list)

    # vision-specific
    covered_items: list[str] = Field(default_factory=list)
    excluded_items: list[str] = Field(default_factory=list)

    # alternative-medicine-specific
    requires_registered_practitioner: bool | None = None
    max_sessions_per_year: int | None = None
    covered_systems: list[str] = Field(default_factory=list)


class WaitingPeriods(BaseModel):
    initial_waiting_period_days: int
    pre_existing_conditions_days: int
    specific_conditions: dict[str, int]  # e.g. {"diabetes": 90, ...}


class Exclusions(BaseModel):
    conditions: list[str]
    dental_exclusions: list[str] = Field(default_factory=list)
    vision_exclusions: list[str] = Field(default_factory=list)


class PreAuthorization(BaseModel):
    required_for: list[str]
    validity_days: int


class DocumentRequirement(BaseModel):
    required: list[str]
    optional: list[str] = Field(default_factory=list)


class SubmissionRules(BaseModel):
    deadline_days_from_treatment: int
    minimum_claim_amount: float
    currency: str


class FraudThresholds(BaseModel):
    same_day_claims_limit: int
    monthly_claims_limit: int
    high_value_claim_threshold: float
    auto_manual_review_above: float
    fraud_score_manual_review_threshold: float


class Member(BaseModel):
    """An employee or a dependent. Employee-only and dependent-only fields are
    optional so one model covers both rows in the roster."""

    member_id: str
    name: str
    date_of_birth: date
    gender: str
    relationship: str
    join_date: date | None = None  # employees only
    dependents: list[str] = Field(default_factory=list)  # employees only
    primary_member_id: str | None = None  # dependents only


class Policy(BaseModel):
    """The whole policy document, plus normalized lookups."""

    policy_id: str
    policy_name: str
    insurer: str
    policy_holder: PolicyHolder
    coverage: Coverage
    opd_categories: dict[str, OpdCategory]
    waiting_periods: WaitingPeriods
    exclusions: Exclusions
    pre_authorization: PreAuthorization
    network_hospitals: list[str]
    submission_rules: SubmissionRules
    document_requirements: dict[str, DocumentRequirement]
    fraud_thresholds: FraudThresholds
    members: list[Member]

    # --- Normalized lookups (absorb the file's casing inconsistencies once) ---

    def get_member(self, member_id: str) -> Member | None:
        """Find a member by id, or None if not in the roster."""
        return next((m for m in self.members if m.member_id == member_id), None)

    def get_category(self, category: str) -> OpdCategory | None:
        """Look up a coverage category. `opd_categories` keys are lowercase in
        the file (e.g. 'consultation') while claims use UPPERCASE."""
        return self.opd_categories.get(category.lower())

    def document_requirement(self, category: str) -> DocumentRequirement | None:
        """Look up required/optional docs for a claim category. These keys are
        UPPERCASE in the file (e.g. 'CONSULTATION')."""
        return self.document_requirements.get(category.upper())
