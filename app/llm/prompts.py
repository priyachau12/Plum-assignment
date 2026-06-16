"""Prompt templates for the LLM nodes.

Kept in one place so prompts can be reviewed/iterated without touching logic.
Each prompt asks for STRICT, parseable output (JSON or a single token) which the
client then validates. On the vision path these prompts accompany an image/PDF
content block, so "this document" refers to the attached file.
"""

from __future__ import annotations

CLASSIFICATION_PROMPT = """You are triaging a medical document attached to an insurance claim.
Look at the attached document image/PDF (if no document is attached, use the file
name as your only clue) and return ONLY a JSON object, no prose:

{{
  "document_type": one of PRESCRIPTION, HOSPITAL_BILL, PHARMACY_BILL, LAB_REPORT,
                   DIAGNOSTIC_REPORT, DISCHARGE_SUMMARY, DENTAL_REPORT, or null if unsure,
  "readable": true if the document is legible enough to extract details, false if it
              is too blurry/dark/cropped to read,
  "patient_name": the patient's full name as printed on the document, or null
}}

File name: {file_name}
"""

EXTRACTION_PROMPT = """Extract structured fields from this attached {document_type} as JSON.
Read the attached document image/PDF. Include any of these keys you can find:
patient_name, doctor_name, doctor_registration, date, diagnosis, treatment,
medicines (list), tests_ordered (list), hospital_name,
line_items (list of {{description, amount}}), total.
Return ONLY valid JSON, no prose.

File name: {file_name}
"""

EXPLANATION_PROMPT = """Rewrite the following claim decision as a clear, friendly,
2-4 sentence explanation for the member. Output ONLY the explanation text — no
preamble, no greeting, no markdown headers. Do not change any numbers or the
decision. Use the Indian rupee sign (Rs.) for every amount; never use $. Be
specific about amounts and reasons. If the factual summary contains a caveat or
recommendation (for example that the claim is provisional or that manual review
is recommended), you MUST keep it — do not imply the payout is final when it is not.

Decision: {decision}
Approved amount: {approved_amount}
Reasons: {reasons}
Factual summary: {fallback}
"""
