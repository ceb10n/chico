"""Implementation of the ``chico status`` command.

Displays the persisted state from ``~/.chico/state.json``: the last run
summary, tracked source versions, and per-source resource details.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from rich.markup import escape

from chico.cli.output import get_console
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
    console = get_console()

    console.print(f"[bold]Status:[/bold] {escape(state.status)}\n")

    if state.last_run is None:
        console.print("[dim]No previous runs recorded.[/dim]")
    else:
        ts = state.last_run.get("timestamp", "unknown")
        applied = state.last_run.get("applied", 0)
        errors = state.last_run.get("errors", 0)
        console.print(f"[dim]Last run:[/dim] {escape(str(ts))}")
        console.print(f"  [dim]Applied:[/dim] {applied}")
        console.print(f"  [dim]Errors:[/dim]  {errors}")

    console.print("")

    if not state.versions:
        console.print("[dim]Sources: no sources tracked yet.[/dim]")
        console.print("")
        console.print(f"[dim]Resources:[/dim] {len(state.resources)} tracked")
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

    console.print(f"[bold]Sources ({len(state.versions)}):[/bold]\n")
    for name, version in state.versions.items():
        short_sha = version[:12] if len(version) > 12 else version
        resources = by_source.get(name, [])
        ok = sum(1 for r in resources if r.get("status") == "ok")
        errors = sum(1 for r in resources if r.get("status") == "error")
        console.print(f"  [bold]{escape(name)}[/bold]")
        console.print(f"    [dim]version:[/dim]   {escape(short_sha)}")
        console.print(
            f"    [dim]resources:[/dim] {len(resources)}"
            f" ([green]{ok} ok[/green], [red]{errors} error[/red])"
        )

    if untagged:
        console.print("\n  [dim](untagged)[/dim]")
        console.print(f"    [dim]resources:[/dim] {len(untagged)}")

    console.print("")
    console.print(f"[dim]Total resources:[/dim] {len(state.resources)} tracked")

    logger.info("status.completed")
