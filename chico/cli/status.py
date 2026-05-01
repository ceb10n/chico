"""Implementation of the ``chico status`` command.

Displays the persisted state from ``~/.chico/state.json``: the last run
summary, tracked source versions, and per-source resource details.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import typer

from chico.core.state import ResourceRecord, load_state

logger = logging.getLogger("chico")


def status() -> None:
    """Show the current chico state.

    Reads ``~/.chico/state.json`` and prints a summary of the last apply
    run, the tracked version (commit SHA) for each configured source,
    and per-source resource details. Does not contact any remote sources.
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

    if not state.versions:
        typer.echo("Sources: no sources tracked yet.")
        typer.echo("")
        typer.echo(f"Resources: {len(state.resources)} tracked")
        logger.info("status.completed")
        return

    # Group resources by source
    by_source: dict[str, list[ResourceRecord]] = defaultdict(list)
    untagged: list[ResourceRecord] = []
    for r in state.resources:
        source_name = r.get("source", "")
        if source_name:
            by_source[source_name].append(r)
        else:
            untagged.append(r)

    typer.echo(f"Sources ({len(state.versions)}):\n")
    for name, version in state.versions.items():
        short_sha = version[:12] if len(version) > 12 else version
        resources = by_source.get(name, [])
        ok = sum(1 for r in resources if r.get("status") == "ok")
        errors = sum(1 for r in resources if r.get("status") == "error")
        typer.echo(f"  {name}")
        typer.echo(f"    version:   {short_sha}")
        typer.echo(f"    resources: {len(resources)} ({ok} ok, {errors} error)")

    if untagged:
        typer.echo("\n  (untagged)")
        typer.echo(f"    resources: {len(untagged)}")

    typer.echo("")
    typer.echo(f"Total resources: {len(state.resources)} tracked")

    logger.info("status.completed")
