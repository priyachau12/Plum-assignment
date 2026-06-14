"""Policy file loader.

Purpose
-------
Read `policy_terms.json` from disk and return a validated `Policy` object.

Why it exists
-------------
The system must apply rules *from the file*, so loading is a first-class step.
Isolating it here means: one place handles I/O + parse + validation, and every
distinct failure mode maps to a single, explainable `PolicyLoadError`.

Interactions
------------
- Called by `main.py` during startup with `settings.policy_file_path`.
- Returns a `models.policy.Policy`, stored on `app.state.policy`.
- Raises `PolicyLoadError` (from `exceptions.py`) on any failure.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.exceptions import PolicyLoadError
from app.models.policy import Policy

logger = logging.getLogger(__name__)


def load_policy(path: Path) -> Policy:
    """Load, parse, and validate the policy file at `path`.

    Three distinct failure modes are collapsed into one typed error so callers
    only handle `PolicyLoadError`, while the message preserves the root cause:
      1. file unreadable/missing  -> OSError
      2. not valid JSON           -> json.JSONDecodeError
      3. JSON shape wrong         -> pydantic.ValidationError
    """
    logger.info("Loading policy from %s", path)

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyLoadError(f"Could not read policy file at {path}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(f"Policy file at {path} is not valid JSON: {exc}") from exc

    try:
        policy = Policy.model_validate(data)
    except ValidationError as exc:
        raise PolicyLoadError(
            f"Policy file at {path} does not match the expected schema: {exc}"
        ) from exc

    logger.info(
        "Policy %s loaded: %d categories, %d members",
        policy.policy_id,
        len(policy.opd_categories),
        len(policy.members),
    )
    return policy
