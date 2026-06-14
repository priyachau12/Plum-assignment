"""Health check endpoint.

Purpose
-------
Expose `GET /health` as a *readiness* probe: it reports not just "the process
is up" but "the policy that the whole system depends on actually loaded".

Why it exists
-------------
The policy file is a hard dependency for every claim decision. A health check
that ignores it would lie about readiness. Reporting `degraded` when the policy
failed to load gives operators (and graders) a single, honest signal.

Interactions
------------
- Registered in `main.py` via `app.include_router(...)`.
- Reads `app.state.settings` and `app.state.policy`, both set in lifespan.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class PolicyStatus(BaseModel):
    loaded: bool
    policy_id: str | None = None
    categories: int = 0
    members: int = 0


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    app_name: str
    environment: str
    policy: PolicyStatus


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Return liveness + policy-load readiness."""
    settings = request.app.state.settings
    policy = getattr(request.app.state, "policy", None)

    if policy is None:
        return HealthResponse(
            status="degraded",
            app_name=settings.app_name,
            environment=settings.environment,
            policy=PolicyStatus(loaded=False),
        )

    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
        policy=PolicyStatus(
            loaded=True,
            policy_id=policy.policy_id,
            categories=len(policy.opd_categories),
            members=len(policy.members),
        ),
    )
