"""Prompt templates for the LLM nodes.

Kept in one place so prompts can be reviewed/iterated without touching logic.
Each prompt asks for STRICT, parseable output (JSON or a single token) which the
client then validates.
"""

from __future__ import annotations

CLASSIFICATION_PROMPT = """You are classifying a medical document for an insurance claim.
Respond with EXACTLY ONE of these labels and nothing else:
PRESCRIPTION, HOSPITAL_BILL, PHARMACY_BILL, LAB_REPORT,
DIAGNOSTIC_REPORT, DISCHARGE_SUMMARY, DENTAL_REPORT.

Document file name: {file_name}
"""

EXTRACTION_PROMPT = """Extract structured fields from this {document_type} as JSON.
Include any of these keys you can find: patient_name, doctor_name,
doctor_registration, date, diagnosis, treatment, medicines (list),
tests_ordered (list), hospital_name, line_items (list of {{description, amount}}),
total. Return ONLY valid JSON, no prose.

Document file name: {file_name}
"""

EXPLANATION_PROMPT = """Rewrite the following claim decision as a clear, friendly,
2-4 sentence explanation for the member. Do not change any numbers or the
decision. Be specific about amounts and reasons.

Decision: {decision}
Approved amount: {approved_amount}
Reasons: {reasons}
Factual summary: {fallback}
"""
