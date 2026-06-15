"""Generate the eval report: run all 12 test cases and write docs/EVAL_REPORT.md.

Runs offline (USE_LLM=false) so the report is deterministic. For each case it
asserts the assignment's per-case `system_must` requirements — not just the
decision and amount, but the message specificity, eligibility dates, confidence
bounds, fraud signals, and discount-before-co-pay breakdown. Usage:

    .venv/bin/python scripts/run_eval.py
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("USE_LLM", "false")  # deterministic, no network
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `app` importable

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]


def _text(body: dict) -> str:
    """All member-facing text the case might assert against."""
    parts = [body.get("note") or "", body.get("explanation") or ""]
    parts += [i.get("message", "") for i in body.get("blocking_issues", [])]
    return " ".join(parts)


def _block_reasons(body: dict) -> set[str]:
    return {i["reason"] for i in body.get("blocking_issues", [])}


def _fb(body: dict) -> dict:
    return body.get("financial_breakdown") or {}


def _rej(body: dict) -> list:
    return body.get("rejection_reasons", [])


def _has_text(body: dict, *needles: str) -> bool:
    text = _text(body).lower()
    return all(n.lower() in text for n in needles)


def _tc006_itemized(body: dict) -> bool:
    lines = body.get("line_items", [])
    covered = any(li["covered"] for li in lines)
    rejected_with_reason = any(not li["covered"] and li.get("reason") for li in lines)
    return covered and rejected_with_reason


def _discount_before_copay(body: dict) -> bool:
    return _fb(body).get("after_network_discount") == 3600 and _fb(body).get("after_copay") == 3240


# Per-case checks derived directly from each case's `expected` / `system_must`.
# A case passes iff EVERY check passes.
Check = tuple[str, Callable[[dict], bool]]
CHECKS: dict[str, list[Check]] = {
    "TC001": [
        ("stops before any decision (BLOCKED)",
         lambda b: b["status"] == "BLOCKED" and b.get("decision") is None),
        ("names the uploaded type AND the required type",
         lambda b: _has_text(b, "PRESCRIPTION", "HOSPITAL_BILL")),
        ("flags the missing required document",
         lambda b: "MISSING_REQUIRED_DOCUMENT" in _block_reasons(b)),
    ],
    "TC002": [
        ("identifies the unreadable document",
         lambda b: "UNREADABLE_DOCUMENT" in _block_reasons(b)),
        ("asks to re-upload that specific document",
         lambda b: _has_text(b, "re-upload")),
        ("does NOT reject the claim",
         lambda b: _has_text(b, "not been rejected") and b.get("decision") is None),
    ],
    "TC003": [
        ("detects documents for different patients",
         lambda b: "PATIENT_MISMATCH" in _block_reasons(b)),
        ("surfaces both specific names",
         lambda b: _has_text(b, "Rajesh Kumar", "Arjun Mehta")),
        ("does not proceed to a decision", lambda b: b.get("decision") is None),
    ],
    "TC004": [
        ("APPROVED", lambda b: b.get("decision") == "APPROVED"),
        ("approved amount 1350 (10% co-pay)", lambda b: b.get("approved_amount") == 1350),
        ("confidence above 0.85", lambda b: (b.get("confidence") or 0) > 0.85),
    ],
    "TC005": [
        ("REJECTED for WAITING_PERIOD",
         lambda b: b.get("decision") == "REJECTED" and "WAITING_PERIOD" in _rej(b)),
        ("states the eligibility date 2024-11-30", lambda b: "2024-11-30" in _text(b)),
    ],
    "TC006": [
        ("PARTIAL", lambda b: b.get("decision") == "PARTIAL"),
        ("approved amount 8000 (root canal only)", lambda b: b.get("approved_amount") == 8000),
        ("itemizes covered vs rejected lines with a per-line reason", _tc006_itemized),
    ],
    "TC007": [
        ("REJECTED for PRE_AUTH_MISSING",
         lambda b: b.get("decision") == "REJECTED" and "PRE_AUTH_MISSING" in _rej(b)),
        ("explains pre-authorization was required", lambda b: _has_text(b, "pre-auth")),
        ("tells the member to resubmit with pre-auth", lambda b: _has_text(b, "resubmit")),
    ],
    "TC008": [
        ("REJECTED for PER_CLAIM_EXCEEDED",
         lambda b: b.get("decision") == "REJECTED" and "PER_CLAIM_EXCEEDED" in _rej(b)),
        ("states the limit (5000) and the claimed amount (7500)",
         lambda b: _has_text(b, "5000", "7500")),
    ],
    "TC009": [
        ("routed to MANUAL_REVIEW (not auto-rejected)",
         lambda b: b.get("decision") == "MANUAL_REVIEW"),
        ("includes the specific signal that triggered the flag",
         lambda b: "SAME_DAY" in _text(b) or "SAME_DAY" in str(_fb(b))),
    ],
    "TC010": [
        ("APPROVED", lambda b: b.get("decision") == "APPROVED"),
        ("approved amount 3240", lambda b: b.get("approved_amount") == 3240),
        ("network discount applied BEFORE co-pay (3600 then 3240)", _discount_before_copay),
    ],
    "TC011": [
        ("does not crash; still produces an APPROVED decision",
         lambda b: b.get("status") == "DECIDED" and b.get("decision") == "APPROVED"),
        ("marks the run degraded", lambda b: b.get("degraded") is True),
        ("confidence reduced below a clean approval", lambda b: (b.get("confidence") or 1) < 0.95),
        ("recommends manual review due to incomplete processing",
         lambda b: _has_text(b, "manual review")),
    ],
    "TC012": [
        ("REJECTED for EXCLUDED_CONDITION",
         lambda b: b.get("decision") == "REJECTED" and "EXCLUDED_CONDITION" in _rej(b)),
        ("confidence above 0.90", lambda b: (b.get("confidence") or 0) > 0.90),
    ],
}


def _run_checks(case_id: str, body: dict) -> list[tuple[str, bool]]:
    results = []
    for desc, predicate in CHECKS.get(case_id, []):
        try:
            ok = bool(predicate(body))
        except Exception:  # noqa: BLE001 - a missing field is a failed check
            ok = False
        results.append((desc, ok))
    return results


def main() -> None:
    get_settings.cache_clear()
    app = create_app()
    rows: list[str] = []
    details: list[str] = []
    passed = 0

    with TestClient(app) as client:
        for case in CASES:
            cid = case["case_id"]
            body = client.post("/claims", json=case["input"]).json()
            checks = _run_checks(cid, body)
            ok = all(result for _, result in checks)
            passed += ok

            summary = body.get("decision") or body.get("status") or "?"
            extra = ""
            if body.get("approved_amount") is not None:
                extra = f"Rs.{body['approved_amount']}"
            elif body.get("blocking_issues"):
                extra = body["blocking_issues"][0]["reason"]
            elif body.get("rejection_reasons"):
                extra = ", ".join(body["rejection_reasons"])
            rows.append(
                f"| {cid} | {case['case_name']} | {summary} {extra} | "
                f"{sum(r for _, r in checks)}/{len(checks)} | {'✅' if ok else '❌'} |"
            )

            check_lines = "\n".join(
                f"- {'✅' if r else '❌'} {desc}" for desc, r in checks
            )
            details.append(
                f"### {cid} — {case['case_name']}\n\n"
                f"**Result:** {'✅ PASS' if ok else '❌ MISMATCH'}\n\n"
                f"**`system_must` checks:**\n\n{check_lines}\n\n"
                f"**Full decision output:**\n\n```json\n{json.dumps(body, indent=2)}\n```\n"
            )

    out = [
        "# Eval Report — all 12 test cases",
        "",
        f"**Result: {passed}/{len(CASES)} cases match every expected outcome and "
        "`system_must` requirement.** Run offline (no LLM) so the output is deterministic. "
        "Each case is checked against its full requirements — decision, amount, message "
        "specificity, eligibility dates, confidence bounds, fraud signals, and the "
        "discount-before-co-pay breakdown — not just the headline decision.",
        "",
        "| Case | Name | Actual | Checks | Match |",
        "|------|------|--------|--------|-------|",
        *rows,
        "",
        "---",
        "",
        "## Per-case detail",
        "",
        *details,
    ]
    report = ROOT / "docs" / "EVAL_REPORT.md"
    report.write_text("\n".join(out), encoding="utf-8")
    print(f"{passed}/{len(CASES)} cases passed all checks. Report written to {report}")


if __name__ == "__main__":
    main()
