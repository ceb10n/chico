"""Implementation of the ``chico status`` command.

Displays the persisted state from ``~/.chico/state.json``: the last run
summary, tracked source versions, and the count of managed resources.
"""

from __future__ import annotations

import logging

import typer

from chico.core.state import load_state

logger = logging.getLogger("chico")


def status() -> None:
    """Show the current chico state.

    Reads ``~/.chico/state.json`` and prints a summary of the last apply
    run, the tracked version (commit SHA) for each configured source, and
    the total number of managed resources. Does not contact any remote
    sources.
    """
    logger.info("status.started")

    state = load_state()

    typer.echo(f"Status: {state.status}\n")

    if state.last_run is None:
        typer.echo("No previous runs recorded.")
    else:
        ts = state.last_run.get("timestamp", "unknown")
        applied = state.last_run.get("applied", 0)
        errors = state.last_run.get("errors", 0)
        typer.echo(f"Last run: {ts}")
        typer.echo(f"  Applied: {applied}")
        typer.echo(f"  Errors:  {errors}")

    typer.echo("")

    if state.versions:
        typer.echo("Sources:")
        for name, version in state.versions.items():
            typer.echo(f"  {name}    {version}")
    else:
        typer.echo("Sources: no sources tracked yet.")

    typer.echo("")
    typer.echo(f"Resources: {len(state.resources)} tracked")

    logger.info("status.completed")
