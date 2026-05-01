"""Shared Rich console factory for chico CLI output.

Consoles are constructed at call time — not at import time — so that
``typer.testing.CliRunner`` can capture output correctly (it patches
``sys.stdout`` and ``sys.stderr`` before invoking the command).
"""

from __future__ import annotations

import sys

from rich.console import Console


def get_console() -> Console:
    """Return a Console writing to the current ``sys.stdout``."""
    return Console(file=sys.stdout, highlight=False)


def get_err_console() -> Console:
    """Return a Console writing to the current ``sys.stderr``."""
    return Console(file=sys.stderr, highlight=False)
