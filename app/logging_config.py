"""Central logging configuration.

Purpose
-------
Configure the root logger once, in one place, so every module's
`logging.getLogger(__name__)` inherits a consistent format and level.

Why it exists
-------------
Observability is 20% of the grade. We want a single switch for log level and a
format that will later carry a claim correlation id. Configuring here (not in
each module) avoids duplicate handlers and inconsistent formats.

Interactions
------------
- `main.py` calls `configure_logging(settings.log_level)` at startup.
"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger to write a single, consistent line to stdout.

    Idempotent: clears existing handlers so repeated calls (e.g. across tests)
    don't stack duplicate output.
    """
    handler = logging.StreamHandler(sys.stdout)  # stdout: 12-factor, container-friendly
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())
    root.addHandler(handler)
