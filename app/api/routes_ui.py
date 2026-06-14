"""UI + sample-claims endpoints.

Purpose
-------
Serve a single-page UI for claim submission and decision review, plus a
`GET /sample-claims` endpoint that returns the 12 provided test cases so the UI
can offer them as one-click examples.

Why it exists
-------------
The assignment requires a UI for submission and review. A tiny static page +
two endpoints is the simplest thing that demonstrates the whole system
(early-stop messages, decisions, and the full trace) without a frontend build.

Interactions
------------
- `GET /` returns `app/static/index.html`.
- `GET /sample-claims` reads the read-only `test_cases.json`.
- Registered in `main.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter(tags=["ui"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/sample-claims")
def sample_claims(request: Request) -> JSONResponse:
    """Return the provided test cases (id, name, input) for the UI dropdown."""
    settings = request.app.state.settings
    path = settings.policy_file_path.parent / "test_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))["test_cases"]
    return JSONResponse(
        [{"case_id": c["case_id"], "case_name": c["case_name"], "input": c["input"]} for c in cases]
    )
