# Eval Report — all 12 test cases

**Result: 12/12 cases match every expected outcome and `system_must` requirement.** Run offline (no LLM) so the output is deterministic. Each case is checked against its full requirements — decision, amount, message specificity, eligibility dates, confidence bounds, fraud signals, and the discount-before-co-pay breakdown — not just the headline decision.

| Case | Name | Actual | Checks | Match |
|------|------|--------|--------|-------|
| TC001 | Wrong Document Uploaded | BLOCKED MISSING_REQUIRED_DOCUMENT | 3/3 | ✅ |
| TC002 | Unreadable Document | BLOCKED UNREADABLE_DOCUMENT | 3/3 | ✅ |
| TC003 | Documents Belong to Different Patients | BLOCKED PATIENT_MISMATCH | 3/3 | ✅ |
| TC004 | Clean Consultation — Full Approval | APPROVED Rs.1350.0 | 3/3 | ✅ |
| TC005 | Waiting Period — Diabetes | REJECTED Rs.0.0 | 2/2 | ✅ |
| TC006 | Dental Partial Approval — Cosmetic Exclusion | PARTIAL Rs.8000.0 | 3/3 | ✅ |
| TC007 | MRI Without Pre-Authorization | REJECTED Rs.0.0 | 3/3 | ✅ |
| TC008 | Per-Claim Limit Exceeded | REJECTED Rs.0.0 | 2/2 | ✅ |
| TC009 | Fraud Signal — Multiple Same-Day Claims | MANUAL_REVIEW Rs.0.0 | 2/2 | ✅ |
| TC010 | Network Hospital — Discount Applied | APPROVED Rs.3240.0 | 3/3 | ✅ |
| TC011 | Component Failure — Graceful Degradation | APPROVED Rs.4000.0 | 4/4 | ✅ |
| TC012 | Excluded Treatment | REJECTED Rs.0.0 | 2/2 | ✅ |

---

## Per-case detail

### TC001 — Wrong Document Uploaded

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ stops before any decision (BLOCKED)
- ✅ names the uploaded type AND the required type
- ✅ flags the missing required document

**Full decision output:**

```json
{
  "claim_id": "CLM_1584C5AE",
  "status": "BLOCKED",
  "decision": null,
  "approved_amount": null,
  "rejection_reasons": [],
  "line_items": [],
  "confidence": null,
  "degraded": false,
  "blocking_issues": [
    {
      "reason": "MISSING_REQUIRED_DOCUMENT",
      "message": "You uploaded: PRESCRIPTION, PRESCRIPTION. A CONSULTATION claim requires these document(s): PRESCRIPTION, HOSPITAL_BILL. The following required document(s) are missing: HOSPITAL_BILL. Please upload the missing document(s) and resubmit.",
      "details": {
        "required": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ],
        "uploaded": [
          "PRESCRIPTION",
          "PRESCRIPTION"
        ],
        "missing": [
          "HOSPITAL_BILL"
        ]
      }
    }
  ],
  "explanation": null,
  "financial_breakdown": null,
  "note": "Claim stopped at document verification. See blocking_issues for what to fix.",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP001, category CONSULTATION, claimed amount 1500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F001: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F001",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F002: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F002",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "BLOCKED",
      "detail": "You uploaded: PRESCRIPTION, PRESCRIPTION. A CONSULTATION claim requires these document(s): PRESCRIPTION, HOSPITAL_BILL. The following required document(s) are missing: HOSPITAL_BILL. Please upload the missing document(s) and resubmit.",
      "data": {
        "missing": [
          "HOSPITAL_BILL"
        ],
        "uploaded": [
          "PRESCRIPTION",
          "PRESCRIPTION"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    }
  ]
}
```

### TC002 — Unreadable Document

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ identifies the unreadable document
- ✅ asks to re-upload that specific document
- ✅ does NOT reject the claim

**Full decision output:**

```json
{
  "claim_id": "CLM_B312532D",
  "status": "BLOCKED",
  "decision": null,
  "approved_amount": null,
  "rejection_reasons": [],
  "line_items": [],
  "confidence": null,
  "degraded": false,
  "blocking_issues": [
    {
      "reason": "UNREADABLE_DOCUMENT",
      "message": "The PHARMACY_BILL (blurry_bill.jpg) could not be read \u2014 the image quality is too low. Please re-upload a clearer photo or scan of this document. Your claim has NOT been rejected; we just need a readable copy.",
      "details": {
        "file_id": "F004",
        "document_type": "PHARMACY_BILL"
      }
    }
  ],
  "explanation": null,
  "financial_breakdown": null,
  "note": "Claim stopped at document verification. See blocking_issues for what to fix.",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP004, category PHARMACY, claimed amount 800.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "PHARMACY"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F003: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F003",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F004: type PHARMACY_BILL (declared by caller).",
      "data": {
        "file_id": "F004",
        "type": "PHARMACY_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for PHARMACY: PRESCRIPTION, PHARMACY_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "PHARMACY_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "BLOCKED",
      "detail": "1 document(s) are unreadable and must be re-uploaded.",
      "data": {
        "unreadable_file_ids": [
          "F004"
        ]
      }
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    }
  ]
}
```

### TC003 — Documents Belong to Different Patients

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ detects documents for different patients
- ✅ surfaces both specific names
- ✅ does not proceed to a decision

**Full decision output:**

```json
{
  "claim_id": "CLM_6BF11367",
  "status": "BLOCKED",
  "decision": null,
  "approved_amount": null,
  "rejection_reasons": [],
  "line_items": [],
  "confidence": null,
  "degraded": false,
  "blocking_issues": [
    {
      "reason": "PATIENT_MISMATCH",
      "message": "The uploaded documents appear to belong to different patients: the PRESCRIPTION names 'Rajesh Kumar'; the HOSPITAL_BILL names 'Arjun Mehta'. All documents in a single claim must be for the same patient. Please check the documents and resubmit.",
      "details": {
        "names_found": {
          "PRESCRIPTION": "Rajesh Kumar",
          "HOSPITAL_BILL": "Arjun Mehta"
        }
      }
    }
  ],
  "explanation": null,
  "financial_breakdown": null,
  "note": "Claim stopped at document verification. See blocking_issues for what to fix.",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP001, category CONSULTATION, claimed amount 1500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F005: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F005",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F006: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F006",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for CONSULTATION: PRESCRIPTION, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "BLOCKED",
      "detail": "The uploaded documents appear to belong to different patients: the PRESCRIPTION names 'Rajesh Kumar'; the HOSPITAL_BILL names 'Arjun Mehta'. All documents in a single claim must be for the same patient. Please check the documents and resubmit.",
      "data": {
        "distinct_names": [
          "arjun mehta",
          "rajesh kumar"
        ]
      }
    }
  ]
}
```

### TC004 — Clean Consultation — Full Approval

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ APPROVED
- ✅ approved amount 1350 (10% co-pay)
- ✅ confidence above 0.85

**Full decision output:**

```json
{
  "claim_id": "CLM_6E7FDAFE",
  "status": "DECIDED",
  "decision": "APPROVED",
  "approved_amount": 1350.0,
  "rejection_reasons": [],
  "line_items": [],
  "confidence": 0.95,
  "degraded": false,
  "blocking_issues": [],
  "explanation": "Your claim was APPROVED for 1350. then a 10% co-pay (-> 1350).",
  "financial_breakdown": {
    "covered_base": 1500.0,
    "is_network": false,
    "network_discount_percent": 0.0,
    "after_network_discount": 1500.0,
    "copay_percent": 10.0,
    "after_copay": 1350.0,
    "per_claim_cap": 5000.0,
    "remaining_annual_opd": 45000.0,
    "approved_amount": 1350.0
  },
  "note": null,
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP001, category CONSULTATION, claimed amount 1500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F007: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F007",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F008: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F008",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for CONSULTATION: PRESCRIPTION, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "All documents name the same patient ('Rajesh Kumar').",
      "data": {}
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F007: used caller-provided structured content.",
      "data": {
        "file_id": "F007",
        "source": "provided"
      }
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F008: used caller-provided structured content.",
      "data": {
        "file_id": "F008",
        "source": "provided"
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Viral Fever' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP001 (Rajesh Kumar) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 1500 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "adjudicate.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "adjudicate.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "adjudicate.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 1500 is within the limit of 5000.",
      "data": {}
    },
    {
      "step": "adjudicate.fraud",
      "status": "OK",
      "detail": "No fraud signals.",
      "data": {}
    },
    {
      "step": "adjudicate.annual_limit",
      "status": "OK",
      "detail": "45000 of the annual OPD limit (50000) remains.",
      "data": {}
    },
    {
      "step": "adjudicate.financials",
      "status": "OK",
      "detail": "covered 1500 -> network discount 0% -> 1500 -> co-pay 10% -> approved 1350.",
      "data": {
        "covered_base": 1500.0,
        "is_network": false,
        "network_discount_percent": 0.0,
        "after_network_discount": 1500.0,
        "copay_percent": 10.0,
        "after_copay": 1350.0,
        "per_claim_cap": 5000.0,
        "remaining_annual_opd": 45000.0,
        "approved_amount": 1350.0
      }
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```

### TC005 — Waiting Period — Diabetes

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ REJECTED for WAITING_PERIOD
- ✅ states the eligibility date 2024-11-30

**Full decision output:**

```json
{
  "claim_id": "CLM_CE1F3A4A",
  "status": "DECIDED",
  "decision": "REJECTED",
  "approved_amount": 0.0,
  "rejection_reasons": [
    "WAITING_PERIOD"
  ],
  "line_items": [],
  "confidence": 0.95,
  "degraded": false,
  "blocking_issues": [],
  "explanation": "Your claim was REJECTED (WAITING_PERIOD). Within the 90-day waiting period for 'diabetes'. Eligible from 2024-11-30.",
  "financial_breakdown": {},
  "note": "Within the 90-day waiting period for 'diabetes'. Eligible from 2024-11-30.",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP005, category CONSULTATION, claimed amount 3000.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F009: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F009",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F010: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F010",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for CONSULTATION: PRESCRIPTION, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "All documents name the same patient ('Vikram Joshi').",
      "data": {}
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F009: used caller-provided structured content.",
      "data": {
        "file_id": "F009",
        "source": "provided"
      }
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F010: used caller-provided structured content.",
      "data": {
        "file_id": "F010",
        "source": "provided"
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Type 2 Diabetes Mellitus' -> waiting_condition=diabetes, excluded_condition=None",
      "data": {
        "waiting_condition": "diabetes",
        "excluded_condition": null
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP005 (Vikram Joshi) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 3000 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "adjudicate.waiting_period",
      "status": "BLOCKED",
      "detail": "'diabetes' has a 90-day waiting period; member joined 2024-09-01, eligible from 2024-11-30, treatment on 2024-10-15.",
      "data": {}
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```

### TC006 — Dental Partial Approval — Cosmetic Exclusion

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ PARTIAL
- ✅ approved amount 8000 (root canal only)
- ✅ itemizes covered vs rejected lines with a per-line reason

**Full decision output:**

```json
{
  "claim_id": "CLM_8EF4C1AE",
  "status": "DECIDED",
  "decision": "PARTIAL",
  "approved_amount": 8000.0,
  "rejection_reasons": [],
  "line_items": [
    {
      "description": "Root Canal Treatment",
      "amount": 8000.0,
      "covered": true,
      "reason": null
    },
    {
      "description": "Teeth Whitening",
      "amount": 4000.0,
      "covered": false,
      "reason": "Excluded procedure under this policy"
    }
  ],
  "confidence": 0.95,
  "degraded": false,
  "blocking_issues": [],
  "explanation": "Your claim was PARTIALLY approved for 8000. Approved: Root Canal Treatment (8000). Not approved: Teeth Whitening (4000) \u2014 excluded under the policy.",
  "financial_breakdown": {
    "covered_base": 8000.0,
    "is_network": false,
    "network_discount_percent": 0.0,
    "after_network_discount": 8000.0,
    "copay_percent": 0.0,
    "after_copay": 8000.0,
    "per_claim_cap": 10000.0,
    "remaining_annual_opd": 50000.0,
    "approved_amount": 8000.0
  },
  "note": null,
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP002, category DENTAL, claimed amount 12000.0, with 1 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "DENTAL"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F011: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F011",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for DENTAL: HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "All documents name the same patient ('Priya Singh').",
      "data": {}
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F011: used caller-provided structured content.",
      "data": {
        "file_id": "F011",
        "source": "provided"
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP002 (Priya Singh) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 12000 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "adjudicate.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "adjudicate.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "adjudicate.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 8000 is within the limit of 10000.",
      "data": {}
    },
    {
      "step": "adjudicate.fraud",
      "status": "OK",
      "detail": "No fraud signals.",
      "data": {}
    },
    {
      "step": "adjudicate.annual_limit",
      "status": "OK",
      "detail": "50000 of the annual OPD limit (50000) remains.",
      "data": {}
    },
    {
      "step": "adjudicate.financials",
      "status": "OK",
      "detail": "covered 8000 -> network discount 0% -> 8000 -> co-pay 0% -> approved 8000.",
      "data": {
        "covered_base": 8000.0,
        "is_network": false,
        "network_discount_percent": 0.0,
        "after_network_discount": 8000.0,
        "copay_percent": 0.0,
        "after_copay": 8000.0,
        "per_claim_cap": 10000.0,
        "remaining_annual_opd": 50000.0,
        "approved_amount": 8000.0
      }
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```

### TC007 — MRI Without Pre-Authorization

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ REJECTED for PRE_AUTH_MISSING
- ✅ explains pre-authorization was required
- ✅ tells the member to resubmit with pre-auth

**Full decision output:**

```json
{
  "claim_id": "CLM_08B56C93",
  "status": "DECIDED",
  "decision": "REJECTED",
  "approved_amount": 0.0,
  "rejection_reasons": [
    "PRE_AUTH_MISSING"
  ],
  "line_items": [],
  "confidence": 0.95,
  "degraded": false,
  "blocking_issues": [],
  "explanation": "Your claim was REJECTED (PRE_AUTH_MISSING). Pre-authorization is required for MRI above 10000 and was not obtained. Obtain pre-auth and resubmit.",
  "financial_breakdown": {},
  "note": "Pre-authorization is required for MRI above 10000 and was not obtained. Obtain pre-auth and resubmit.",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP007, category DIAGNOSTIC, claimed amount 15000.0, with 3 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "DIAGNOSTIC"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F012: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F012",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F013: type LAB_REPORT (declared by caller).",
      "data": {
        "file_id": "F013",
        "type": "LAB_REPORT",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F014: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F014",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for DIAGNOSTIC: PRESCRIPTION, LAB_REPORT, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "LAB_REPORT",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F012: used caller-provided structured content.",
      "data": {
        "file_id": "F012",
        "source": "provided"
      }
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F013: used caller-provided structured content.",
      "data": {
        "file_id": "F013",
        "source": "provided"
      }
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F014: used caller-provided structured content.",
      "data": {
        "file_id": "F014",
        "source": "provided"
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Suspected Lumbar Disc Herniation' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP007 (Suresh Patil) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 15000 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "adjudicate.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "adjudicate.pre_auth",
      "status": "BLOCKED",
      "detail": "MRI above 10000.0 requires pre-authorization; none provided.",
      "data": {}
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```

### TC008 — Per-Claim Limit Exceeded

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ REJECTED for PER_CLAIM_EXCEEDED
- ✅ states the limit (5000) and the claimed amount (7500)

**Full decision output:**

```json
{
  "claim_id": "CLM_245BD5D7",
  "status": "DECIDED",
  "decision": "REJECTED",
  "approved_amount": 0.0,
  "rejection_reasons": [
    "PER_CLAIM_EXCEEDED"
  ],
  "line_items": [],
  "confidence": 0.95,
  "degraded": false,
  "blocking_issues": [],
  "explanation": "Your claim was REJECTED (PER_CLAIM_EXCEEDED). The per-claim limit is 5000; this claim is for 7500.",
  "financial_breakdown": {},
  "note": "The per-claim limit is 5000; this claim is for 7500.",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP003, category CONSULTATION, claimed amount 7500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F015: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F015",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F016: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F016",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for CONSULTATION: PRESCRIPTION, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F015: used caller-provided structured content.",
      "data": {
        "file_id": "F015",
        "source": "provided"
      }
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F016: used caller-provided structured content.",
      "data": {
        "file_id": "F016",
        "source": "provided"
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Gastroenteritis' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP003 (Amit Verma) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 7500 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "adjudicate.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "adjudicate.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "adjudicate.per_claim_limit",
      "status": "BLOCKED",
      "detail": "Covered amount 7500 exceeds the per-claim limit of 5000.",
      "data": {}
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```

### TC009 — Fraud Signal — Multiple Same-Day Claims

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ routed to MANUAL_REVIEW (not auto-rejected)
- ✅ includes the specific signal that triggered the flag

**Full decision output:**

```json
{
  "claim_id": "CLM_9A666FC7",
  "status": "DECIDED",
  "decision": "MANUAL_REVIEW",
  "approved_amount": 0.0,
  "rejection_reasons": [],
  "line_items": [],
  "confidence": 0.9,
  "degraded": false,
  "blocking_issues": [],
  "explanation": "Your claim has been routed to MANUAL REVIEW. Routed to manual review due to fraud signals: SAME_DAY_CLAIMS: 4 claims on 2024-10-30 exceeds limit of 2",
  "financial_breakdown": {
    "signals": [
      "SAME_DAY_CLAIMS: 4 claims on 2024-10-30 exceeds limit of 2"
    ]
  },
  "note": "Routed to manual review due to fraud signals: SAME_DAY_CLAIMS: 4 claims on 2024-10-30 exceeds limit of 2",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP008, category CONSULTATION, claimed amount 4800.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F017: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F017",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F018: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F018",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for CONSULTATION: PRESCRIPTION, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F017: used caller-provided structured content.",
      "data": {
        "file_id": "F017",
        "source": "provided"
      }
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F018: used caller-provided structured content.",
      "data": {
        "file_id": "F018",
        "source": "provided"
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Migraine' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP008 (Ravi Menon) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 4800 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "adjudicate.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "adjudicate.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "adjudicate.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 4800 is within the limit of 5000.",
      "data": {}
    },
    {
      "step": "adjudicate.fraud",
      "status": "BLOCKED",
      "detail": "SAME_DAY_CLAIMS: 4 claims on 2024-10-30 exceeds limit of 2",
      "data": {
        "signals": [
          "SAME_DAY_CLAIMS: 4 claims on 2024-10-30 exceeds limit of 2"
        ]
      }
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```

### TC010 — Network Hospital — Discount Applied

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ APPROVED
- ✅ approved amount 3240
- ✅ network discount applied BEFORE co-pay (3600 then 3240)

**Full decision output:**

```json
{
  "claim_id": "CLM_876976B3",
  "status": "DECIDED",
  "decision": "APPROVED",
  "approved_amount": 3240.0,
  "rejection_reasons": [],
  "line_items": [],
  "confidence": 0.95,
  "degraded": false,
  "blocking_issues": [],
  "explanation": "Your claim was APPROVED for 3240. A 20% network discount was applied first (4500 -> 3600), then a 10% co-pay (-> 3240).",
  "financial_breakdown": {
    "covered_base": 4500.0,
    "is_network": true,
    "network_discount_percent": 20.0,
    "after_network_discount": 3600.0,
    "copay_percent": 10.0,
    "after_copay": 3240.0,
    "per_claim_cap": 5000.0,
    "remaining_annual_opd": 42000.0,
    "approved_amount": 3240.0
  },
  "note": null,
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP010, category CONSULTATION, claimed amount 4500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F019: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F019",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F020: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F020",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for CONSULTATION: PRESCRIPTION, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "All documents name the same patient ('Deepak Shah').",
      "data": {}
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F019: used caller-provided structured content.",
      "data": {
        "file_id": "F019",
        "source": "provided"
      }
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F020: used caller-provided structured content.",
      "data": {
        "file_id": "F020",
        "source": "provided"
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Acute Bronchitis' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP010 (Deepak Shah) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 4500 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "adjudicate.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "adjudicate.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "adjudicate.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 4500 is within the limit of 5000.",
      "data": {}
    },
    {
      "step": "adjudicate.fraud",
      "status": "OK",
      "detail": "No fraud signals.",
      "data": {}
    },
    {
      "step": "adjudicate.annual_limit",
      "status": "OK",
      "detail": "42000 of the annual OPD limit (50000) remains.",
      "data": {}
    },
    {
      "step": "adjudicate.financials",
      "status": "OK",
      "detail": "covered 4500 -> network discount 20% -> 3600 -> co-pay 10% -> approved 3240.",
      "data": {
        "covered_base": 4500.0,
        "is_network": true,
        "network_discount_percent": 20.0,
        "after_network_discount": 3600.0,
        "copay_percent": 10.0,
        "after_copay": 3240.0,
        "per_claim_cap": 5000.0,
        "remaining_annual_opd": 42000.0,
        "approved_amount": 3240.0
      }
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```

### TC011 — Component Failure — Graceful Degradation

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ does not crash; still produces an APPROVED decision
- ✅ marks the run degraded
- ✅ confidence reduced below a clean approval
- ✅ recommends manual review due to incomplete processing

**Full decision output:**

```json
{
  "claim_id": "CLM_DE5E5736",
  "status": "DECIDED",
  "decision": "APPROVED",
  "approved_amount": 4000.0,
  "rejection_reasons": [],
  "line_items": [],
  "confidence": 0.65,
  "degraded": true,
  "blocking_issues": [],
  "explanation": "Your claim was APPROVED for 4000. A processing component failed and was skipped; manual review is recommended due to incomplete processing.",
  "financial_breakdown": {
    "covered_base": 4000.0,
    "is_network": false,
    "network_discount_percent": 0.0,
    "after_network_discount": 4000.0,
    "copay_percent": 0.0,
    "after_copay": 4000.0,
    "per_claim_cap": 8000.0,
    "remaining_annual_opd": 50000.0,
    "approved_amount": 4000.0
  },
  "note": "A processing component failed and was skipped; manual review is recommended due to incomplete processing.",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP006, category ALTERNATIVE_MEDICINE, claimed amount 4000.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "ALTERNATIVE_MEDICINE"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F021: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F021",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F022: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F022",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for ALTERNATIVE_MEDICINE: PRESCRIPTION, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "extract",
      "status": "FAILED",
      "detail": "Simulated component failure: extraction skipped. Continuing with available data; confidence reduced.",
      "data": {
        "degraded": true
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Chronic Joint Pain | Panchakarma Therapy' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP006 (Kavita Nair) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 4000 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "adjudicate.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "adjudicate.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "adjudicate.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 4000 is within the limit of 8000.",
      "data": {}
    },
    {
      "step": "adjudicate.fraud",
      "status": "OK",
      "detail": "No fraud signals.",
      "data": {}
    },
    {
      "step": "adjudicate.annual_limit",
      "status": "OK",
      "detail": "50000 of the annual OPD limit (50000) remains.",
      "data": {}
    },
    {
      "step": "adjudicate.financials",
      "status": "OK",
      "detail": "covered 4000 -> network discount 0% -> 4000 -> co-pay 0% -> approved 4000.",
      "data": {
        "covered_base": 4000.0,
        "is_network": false,
        "network_discount_percent": 0.0,
        "after_network_discount": 4000.0,
        "copay_percent": 0.0,
        "after_copay": 4000.0,
        "per_claim_cap": 8000.0,
        "remaining_annual_opd": 50000.0,
        "approved_amount": 4000.0
      }
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```

### TC012 — Excluded Treatment

**Result:** ✅ PASS

**`system_must` checks:**

- ✅ REJECTED for EXCLUDED_CONDITION
- ✅ confidence above 0.90

**Full decision output:**

```json
{
  "claim_id": "CLM_DE4F6924",
  "status": "DECIDED",
  "decision": "REJECTED",
  "approved_amount": 0.0,
  "rejection_reasons": [
    "EXCLUDED_CONDITION"
  ],
  "line_items": [],
  "confidence": 0.95,
  "degraded": false,
  "blocking_issues": [],
  "explanation": "Your claim was REJECTED (EXCLUDED_CONDITION). This claim is for an excluded condition: 'Obesity and weight loss programs'.",
  "financial_breakdown": {},
  "note": "This claim is for an excluded condition: 'Obesity and weight loss programs'.",
  "trace": [
    {
      "step": "intake",
      "status": "OK",
      "detail": "Claim received for member EMP009, category CONSULTATION, claimed amount 8000.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F023: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F023",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "classify",
      "status": "OK",
      "detail": "F024: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F024",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "verify.required_documents",
      "status": "OK",
      "detail": "All required documents present for CONSULTATION: PRESCRIPTION, HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "PRESCRIPTION",
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "verify.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "verify.patient_consistency",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F023: used caller-provided structured content.",
      "data": {
        "file_id": "F023",
        "source": "provided"
      }
    },
    {
      "step": "extract",
      "status": "OK",
      "detail": "F024: used caller-provided structured content.",
      "data": {
        "file_id": "F024",
        "source": "provided"
      }
    },
    {
      "step": "normalize_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Morbid Obesity \u2014 BMI 37 | Bariatric Consultation and Customised Diet Plan' -> waiting_condition=obesity_treatment, excluded_condition=Obesity and weight loss programs",
      "data": {
        "waiting_condition": "obesity_treatment",
        "excluded_condition": "Obesity and weight loss programs"
      }
    },
    {
      "step": "adjudicate.eligibility",
      "status": "OK",
      "detail": "Member EMP009 (Anita Desai) is covered.",
      "data": {}
    },
    {
      "step": "adjudicate.minimum_amount",
      "status": "OK",
      "detail": "Claimed amount 8000 meets the minimum of 500.",
      "data": {}
    },
    {
      "step": "adjudicate.submission_window",
      "status": "OK",
      "detail": "No submission date provided; assumed within the 30-day deadline.",
      "data": {}
    },
    {
      "step": "adjudicate.exclusions",
      "status": "BLOCKED",
      "detail": "Diagnosis/treatment matches a policy exclusion: 'Obesity and weight loss programs'.",
      "data": {}
    },
    {
      "step": "explain",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```
