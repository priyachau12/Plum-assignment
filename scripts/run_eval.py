"""Generate the eval report: run all 12 test cases and write docs/EVAL_REPORT.md.

Runs offline (USE_LLM=false) so the report is deterministic. Usage:

    .venv/bin/python scripts/run_eval.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("USE_LLM", "false")  # deterministic, no network
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # make `app` importable

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "test_cases.json").read_text(encoding="utf-8"))["test_cases"]

# What each case is expected to produce (summary form, from test_cases.json).
EXPECT: dict[str, dict] = {
    "TC001": {"status": "BLOCKED", "blocking": "MISSING_REQUIRED_DOCUMENT"},
    "TC002": {"status": "BLOCKED", "blocking": "UNREADABLE_DOCUMENT"},
    "TC003": {"status": "BLOCKED", "blocking": "PATIENT_MISMATCH"},
    "TC004": {"decision": "APPROVED", "approved_amount": 1350},
    "TC005": {"decision": "REJECTED", "reason": "WAITING_PERIOD"},
    "TC006": {"decision": "PARTIAL", "approved_amount": 8000},
    "TC007": {"decision": "REJECTED", "reason": "PRE_AUTH_MISSING"},
    "TC008": {"decision": "REJECTED", "reason": "PER_CLAIM_EXCEEDED"},
    "TC009": {"decision": "MANUAL_REVIEW"},
    "TC010": {"decision": "APPROVED", "approved_amount": 3240},
    "TC011": {"decision": "APPROVED", "degraded": True},
    "TC012": {"decision": "REJECTED", "reason": "EXCLUDED_CONDITION"},
}


def _matches(exp: dict, body: dict) -> bool:
    if "status" in exp and body.get("status") != exp["status"]:
        return False
    if "blocking" in exp:
        if not any(i["reason"] == exp["blocking"] for i in body.get("blocking_issues", [])):
            return False
    if "decision" in exp and body.get("decision") != exp["decision"]:
        return False
    if "approved_amount" in exp and body.get("approved_amount") != exp["approved_amount"]:
        return False
    if "reason" in exp and exp["reason"] not in body.get("rejection_reasons", []):
        return False
    if "degraded" in exp and body.get("degraded") != exp["degraded"]:
        return False
    return True


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
            exp = EXPECT.get(cid, {})
            ok = _matches(exp, body)
            passed += ok
            summary = body.get("decision") or body.get("status") or "?"
            extra = ""
            if body.get("approved_amount") is not None:
                extra = f"₹{body['approved_amount']}"
            elif body.get("blocking_issues"):
                extra = body["blocking_issues"][0]["reason"]
            elif body.get("rejection_reasons"):
                extra = ", ".join(body["rejection_reasons"])
            rows.append(
                f"| {cid} | {case['case_name']} | {json.dumps(exp)} | {summary} {extra} | "
                f"{'✅' if ok else '❌'} |"
            )
            details.append(
                f"### {cid} — {case['case_name']}\n\n"
                f"**Match:** {'✅ PASS' if ok else '❌ MISMATCH'}\n\n"
                f"```json\n{json.dumps(body, indent=2)}\n```\n"
            )

    out = [
        "# Eval Report — all 12 test cases",
        "",
        f"**Result: {passed}/{len(CASES)} cases match the expected outcome.** "
        "Run offline (no LLM) so the output is deterministic.",
        "",
        "| Case | Name | Expected (summary) | Actual | Match |",
        "|------|------|--------------------|--------|-------|",
        *rows,
        "",
        "---",
        "",
        "## Full decision output per case",
        "",
        *details,
    ]
    report = ROOT / "docs" / "EVAL_REPORT.md"
    report.write_text("\n".join(out), encoding="utf-8")
    print(f"{passed}/{len(CASES)} cases passed. Report written to {report}")


if __name__ == "__main__":
    main()
