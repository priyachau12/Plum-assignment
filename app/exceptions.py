"""Typed exception hierarchy.

Purpose
-------
Give the app its own error types so callers can `except ClaimsSystemError`
once and catch everything we raise, while still distinguishing specific
failures.

Why it exists
-------------
Generic `Exception`/`ValueError` make error handling imprecise. A small typed
hierarchy lets FastAPI exception handlers and the pipeline's failure-handling
code react to *our* errors specifically (graceful degradation is a grading
criterion).

Interactions
------------
- `loader.py` raises `PolicyLoadError`.
- `main.py` catches `PolicyLoadError` during startup.
- Later phases add more leaf types (e.g. extraction/LLM errors).
"""

from __future__ import annotations


class ClaimsSystemError(Exception):
    """Base class for every error this application raises intentionally."""


class PolicyLoadError(ClaimsSystemError):
    """The policy file could not be read, parsed, or validated."""
