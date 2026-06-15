# Eval Report — all 12 test cases

**Result: 12/12 cases match the expected outcome.** Run offline (no LLM) so the output is deterministic.

| Case | Name | Expected (summary) | Actual | Match |
|------|------|--------------------|--------|-------|
| TC001 | Wrong Document Uploaded | {"status": "BLOCKED", "blocking": "MISSING_REQUIRED_DOCUMENT"} | BLOCKED MISSING_REQUIRED_DOCUMENT | ✅ |
| TC002 | Unreadable Document | {"status": "BLOCKED", "blocking": "UNREADABLE_DOCUMENT"} | BLOCKED UNREADABLE_DOCUMENT | ✅ |
| TC003 | Documents Belong to Different Patients | {"status": "BLOCKED", "blocking": "PATIENT_MISMATCH"} | BLOCKED PATIENT_MISMATCH | ✅ |
| TC004 | Clean Consultation — Full Approval | {"decision": "APPROVED", "approved_amount": 1350} | APPROVED ₹1350.0 | ✅ |
| TC005 | Waiting Period — Diabetes | {"decision": "REJECTED", "reason": "WAITING_PERIOD"} | REJECTED ₹0.0 | ✅ |
| TC006 | Dental Partial Approval — Cosmetic Exclusion | {"decision": "PARTIAL", "approved_amount": 8000} | PARTIAL ₹8000.0 | ✅ |
| TC007 | MRI Without Pre-Authorization | {"decision": "REJECTED", "reason": "PRE_AUTH_MISSING"} | REJECTED ₹0.0 | ✅ |
| TC008 | Per-Claim Limit Exceeded | {"decision": "REJECTED", "reason": "PER_CLAIM_EXCEEDED"} | REJECTED ₹0.0 | ✅ |
| TC009 | Fraud Signal — Multiple Same-Day Claims | {"decision": "MANUAL_REVIEW"} | MANUAL_REVIEW ₹0.0 | ✅ |
| TC010 | Network Hospital — Discount Applied | {"decision": "APPROVED", "approved_amount": 3240} | APPROVED ₹3240.0 | ✅ |
| TC011 | Component Failure — Graceful Degradation | {"decision": "APPROVED", "degraded": true} | APPROVED ₹4000.0 | ✅ |
| TC012 | Excluded Treatment | {"decision": "REJECTED", "reason": "EXCLUDED_CONDITION"} | REJECTED ₹0.0 | ✅ |

---

## Full decision output per case

### TC001 — Wrong Document Uploaded

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_7F881ABA",
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
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP001, category CONSULTATION, claimed amount 1500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F001: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F001",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F002: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F002",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    }
  ]
}
```

### TC002 — Unreadable Document

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_DF4A065F",
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
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP004, category PHARMACY, claimed amount 800.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "PHARMACY"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F003: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F003",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F004: type PHARMACY_BILL (declared by caller).",
      "data": {
        "file_id": "F004",
        "type": "PHARMACY_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "BLOCKED",
      "detail": "1 document(s) are unreadable and must be re-uploaded.",
      "data": {
        "unreadable_file_ids": [
          "F004"
        ]
      }
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    }
  ]
}
```

### TC003 — Documents Belong to Different Patients

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_FB6F516F",
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
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP001, category CONSULTATION, claimed amount 1500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F005: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F005",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F006: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F006",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_3013E9D1",
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
    "approved_amount": 1350.0
  },
  "note": null,
  "trace": [
    {
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP001, category CONSULTATION, claimed amount 1500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F007: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F007",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F008: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F008",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "All documents name the same patient ('Rajesh Kumar').",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F007: used caller-provided structured content.",
      "data": {
        "file_id": "F007",
        "source": "provided"
      }
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F008: used caller-provided structured content.",
      "data": {
        "file_id": "F008",
        "source": "provided"
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Viral Fever' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP001 (Rajesh Kumar) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "decide.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "decide.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "decide.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 1500 is within the limit of 5000.",
      "data": {}
    },
    {
      "step": "decide.fraud",
      "status": "OK",
      "detail": "No fraud signals.",
      "data": {}
    },
    {
      "step": "decide.money_math",
      "status": "OK",
      "detail": "covered 1500 -> network discount 0% -> 1500 -> co-pay 10% -> approved 1350.",
      "data": {
        "covered_base": 1500.0,
        "is_network": false,
        "network_discount_percent": 0.0,
        "after_network_discount": 1500.0,
        "copay_percent": 10.0,
        "after_copay": 1350.0,
        "approved_amount": 1350.0
      }
    },
    {
      "step": "write_explanation",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_1454344C",
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
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP005, category CONSULTATION, claimed amount 3000.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F009: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F009",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F010: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F010",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "All documents name the same patient ('Vikram Joshi').",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F009: used caller-provided structured content.",
      "data": {
        "file_id": "F009",
        "source": "provided"
      }
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F010: used caller-provided structured content.",
      "data": {
        "file_id": "F010",
        "source": "provided"
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Type 2 Diabetes Mellitus' -> waiting_condition=diabetes, excluded_condition=None",
      "data": {
        "waiting_condition": "diabetes",
        "excluded_condition": null
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP005 (Vikram Joshi) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "decide.waiting_period",
      "status": "BLOCKED",
      "detail": "'diabetes' has a 90-day waiting period; member joined 2024-09-01, eligible from 2024-11-30, treatment on 2024-10-15.",
      "data": {}
    },
    {
      "step": "write_explanation",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_BB35B6D6",
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
    "approved_amount": 8000.0
  },
  "note": null,
  "trace": [
    {
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP002, category DENTAL, claimed amount 12000.0, with 1 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "DENTAL"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F011: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F011",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
      "status": "OK",
      "detail": "All required documents present for DENTAL: HOSPITAL_BILL.",
      "data": {
        "uploaded": [
          "HOSPITAL_BILL"
        ]
      }
    },
    {
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "All documents name the same patient ('Priya Singh').",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F011: used caller-provided structured content.",
      "data": {
        "file_id": "F011",
        "source": "provided"
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP002 (Priya Singh) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "decide.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "decide.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "decide.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 8000 is within the limit of 10000.",
      "data": {}
    },
    {
      "step": "decide.fraud",
      "status": "OK",
      "detail": "No fraud signals.",
      "data": {}
    },
    {
      "step": "decide.money_math",
      "status": "OK",
      "detail": "covered 8000 -> network discount 0% -> 8000 -> co-pay 0% -> approved 8000.",
      "data": {
        "covered_base": 8000.0,
        "is_network": false,
        "network_discount_percent": 0.0,
        "after_network_discount": 8000.0,
        "copay_percent": 0.0,
        "after_copay": 8000.0,
        "approved_amount": 8000.0
      }
    },
    {
      "step": "write_explanation",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_8E7B81CD",
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
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP007, category DIAGNOSTIC, claimed amount 15000.0, with 3 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "DIAGNOSTIC"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F012: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F012",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F013: type LAB_REPORT (declared by caller).",
      "data": {
        "file_id": "F013",
        "type": "LAB_REPORT",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F014: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F014",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F012: used caller-provided structured content.",
      "data": {
        "file_id": "F012",
        "source": "provided"
      }
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F013: used caller-provided structured content.",
      "data": {
        "file_id": "F013",
        "source": "provided"
      }
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F014: used caller-provided structured content.",
      "data": {
        "file_id": "F014",
        "source": "provided"
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Suspected Lumbar Disc Herniation' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP007 (Suresh Patil) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "decide.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "decide.pre_auth",
      "status": "BLOCKED",
      "detail": "MRI above 10000.0 requires pre-authorization; none provided.",
      "data": {}
    },
    {
      "step": "write_explanation",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_23330E4D",
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
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP003, category CONSULTATION, claimed amount 7500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F015: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F015",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F016: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F016",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F015: used caller-provided structured content.",
      "data": {
        "file_id": "F015",
        "source": "provided"
      }
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F016: used caller-provided structured content.",
      "data": {
        "file_id": "F016",
        "source": "provided"
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Gastroenteritis' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP003 (Amit Verma) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "decide.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "decide.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "decide.per_claim_limit",
      "status": "BLOCKED",
      "detail": "Covered amount 7500 exceeds the per-claim limit of 5000.",
      "data": {}
    },
    {
      "step": "write_explanation",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_450F8928",
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
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP008, category CONSULTATION, claimed amount 4800.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F017: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F017",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F018: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F018",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F017: used caller-provided structured content.",
      "data": {
        "file_id": "F017",
        "source": "provided"
      }
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F018: used caller-provided structured content.",
      "data": {
        "file_id": "F018",
        "source": "provided"
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Migraine' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP008 (Ravi Menon) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "decide.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "decide.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "decide.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 4800 is within the limit of 5000.",
      "data": {}
    },
    {
      "step": "decide.fraud",
      "status": "BLOCKED",
      "detail": "SAME_DAY_CLAIMS: 4 claims on 2024-10-30 exceeds limit of 2",
      "data": {
        "signals": [
          "SAME_DAY_CLAIMS: 4 claims on 2024-10-30 exceeds limit of 2"
        ]
      }
    },
    {
      "step": "write_explanation",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_E40EE21A",
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
    "approved_amount": 3240.0
  },
  "note": null,
  "trace": [
    {
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP010, category CONSULTATION, claimed amount 4500.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F019: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F019",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F020: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F020",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "All documents name the same patient ('Deepak Shah').",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F019: used caller-provided structured content.",
      "data": {
        "file_id": "F019",
        "source": "provided"
      }
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F020: used caller-provided structured content.",
      "data": {
        "file_id": "F020",
        "source": "provided"
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Acute Bronchitis' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP010 (Deepak Shah) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "decide.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "decide.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "decide.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 4500 is within the limit of 5000.",
      "data": {}
    },
    {
      "step": "decide.fraud",
      "status": "OK",
      "detail": "No fraud signals.",
      "data": {}
    },
    {
      "step": "decide.money_math",
      "status": "OK",
      "detail": "covered 4500 -> network discount 20% -> 3600 -> co-pay 10% -> approved 3240.",
      "data": {
        "covered_base": 4500.0,
        "is_network": true,
        "network_discount_percent": 20.0,
        "after_network_discount": 3600.0,
        "copay_percent": 10.0,
        "after_copay": 3240.0,
        "approved_amount": 3240.0
      }
    },
    {
      "step": "write_explanation",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_62B0EF90",
  "status": "DECIDED",
  "decision": "APPROVED",
  "approved_amount": 4000.0,
  "rejection_reasons": [],
  "line_items": [],
  "confidence": 0.65,
  "degraded": true,
  "blocking_issues": [],
  "explanation": "Your claim was APPROVED for 4000.",
  "financial_breakdown": {
    "covered_base": 4000.0,
    "is_network": false,
    "network_discount_percent": 0.0,
    "after_network_discount": 4000.0,
    "copay_percent": 0.0,
    "after_copay": 4000.0,
    "approved_amount": 4000.0
  },
  "note": "A processing component failed and was skipped; manual review is recommended due to incomplete processing.",
  "trace": [
    {
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP006, category ALTERNATIVE_MEDICINE, claimed amount 4000.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "ALTERNATIVE_MEDICINE"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F021: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F021",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F022: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F022",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "FAILED",
      "detail": "Simulated component failure: reading skipped. Continuing with available data; confidence reduced.",
      "data": {
        "degraded": true
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Chronic Joint Pain | Panchakarma Therapy' -> waiting_condition=None, excluded_condition=None",
      "data": {
        "waiting_condition": null,
        "excluded_condition": null
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP006 (Kavita Nair) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "OK",
      "detail": "No policy exclusion matched the diagnosis/treatment.",
      "data": {}
    },
    {
      "step": "decide.waiting_period",
      "status": "OK",
      "detail": "Outside all applicable waiting periods.",
      "data": {}
    },
    {
      "step": "decide.pre_auth",
      "status": "OK",
      "detail": "No pre-authorization requirement triggered.",
      "data": {}
    },
    {
      "step": "decide.per_claim_limit",
      "status": "OK",
      "detail": "Covered amount 4000 is within the limit of 8000.",
      "data": {}
    },
    {
      "step": "decide.fraud",
      "status": "OK",
      "detail": "No fraud signals.",
      "data": {}
    },
    {
      "step": "decide.money_math",
      "status": "OK",
      "detail": "covered 4000 -> network discount 0% -> 4000 -> co-pay 0% -> approved 4000.",
      "data": {
        "covered_base": 4000.0,
        "is_network": false,
        "network_discount_percent": 0.0,
        "after_network_discount": 4000.0,
        "copay_percent": 0.0,
        "after_copay": 4000.0,
        "approved_amount": 4000.0
      }
    },
    {
      "step": "write_explanation",
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

**Match:** ✅ PASS

```json
{
  "claim_id": "CLM_5DBC4C46",
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
      "step": "find_member",
      "status": "OK",
      "detail": "Claim received for member EMP009, category CONSULTATION, claimed amount 8000.0, with 2 document(s).",
      "data": {
        "member_found": true,
        "claim_category": "CONSULTATION"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F023: type PRESCRIPTION (declared by caller).",
      "data": {
        "file_id": "F023",
        "type": "PRESCRIPTION",
        "source": "declared"
      }
    },
    {
      "step": "label_documents",
      "status": "OK",
      "detail": "F024: type HOSPITAL_BILL (declared by caller).",
      "data": {
        "file_id": "F024",
        "type": "HOSPITAL_BILL",
        "source": "declared"
      }
    },
    {
      "step": "check.required_documents",
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
      "step": "check.readability",
      "status": "OK",
      "detail": "All documents are readable.",
      "data": {}
    },
    {
      "step": "check.same_patient",
      "status": "OK",
      "detail": "No patient names were present on the documents to compare.",
      "data": {}
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F023: used caller-provided structured content.",
      "data": {
        "file_id": "F023",
        "source": "provided"
      }
    },
    {
      "step": "read_documents",
      "status": "OK",
      "detail": "F024: used caller-provided structured content.",
      "data": {
        "file_id": "F024",
        "source": "provided"
      }
    },
    {
      "step": "translate_diagnosis",
      "status": "OK",
      "detail": "diagnosis/treatment='Morbid Obesity \u2014 BMI 37 | Bariatric Consultation and Customised Diet Plan' -> waiting_condition=obesity_treatment, excluded_condition=Obesity and weight loss programs",
      "data": {
        "waiting_condition": "obesity_treatment",
        "excluded_condition": "Obesity and weight loss programs"
      }
    },
    {
      "step": "decide.eligibility",
      "status": "OK",
      "detail": "Member EMP009 (Anita Desai) is covered.",
      "data": {}
    },
    {
      "step": "decide.exclusions",
      "status": "BLOCKED",
      "detail": "Diagnosis/treatment matches a policy exclusion: 'Obesity and weight loss programs'.",
      "data": {}
    },
    {
      "step": "write_explanation",
      "status": "OK",
      "detail": "Generated member-facing explanation (template).",
      "data": {
        "source": "template"
      }
    }
  ]
}
```
