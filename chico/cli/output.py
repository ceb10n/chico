"""Shared Rich console factory and progress utilities for chico CLI output.

Consoles are constructed at call time — not at import time — so that
``typer.testing.CliRunner`` can capture output correctly (it patches
``sys.stdout`` and ``sys.stderr`` before invoking the command).
"""

from __future__ import annotations

import itertools
import sys
import threading
from collections.abc import Callable
from typing import TypeVar

from rich.console import Console

T = TypeVar("T")


def get_console() -> Console:
    """Return a Console writing to the current ``sys.stdout``."""
    return Console(file=sys.stdout, highlight=False)


def get_err_console() -> Console:
    """Return a Console writing to the current ``sys.stderr``."""
    return Console(file=sys.stderr, highlight=False)


def run_with_progress(
    console: Console,
    messages: list[str],
    fn: Callable[[], T],
    interval: float = 2.5,
) -> T:
    """Run *fn* in a background thread, cycling *messages* on the console.

    Cycles through *messages* every *interval* seconds while *fn* executes.
    Any exception raised by *fn* is re-raised in the calling thread after it
    completes.

    Parameters
    ----------
    console:
        The Rich console to render progress on.
    messages:
        Non-empty list of status strings to cycle through.
    fn:
        The blocking callable to run. Must return a single value.
    interval:
        Seconds between message updates. Defaults to 2.5 s.
    """
    result: list[T] = []
    caught: list[BaseException] = []

    def _run() -> None:
        try:
            result.append(fn())
        except BaseException as exc:
            caught.append(exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    with console.status("") as status:
        for msg in itertools.cycle(messages):  # pragma: no branch
            status.update(msg)
            thread.join(timeout=interval)
            if not thread.is_alive():
                break

    thread.join()

    if caught:
        raise caught[0]
    return result[0]
