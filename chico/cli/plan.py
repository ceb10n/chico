"""Implementation of the ``chico plan`` command.

Computes the changeset between desired state (from sources) and current local
state (on disk), then prints a human-readable summary.
"""

from __future__ import annotations

import logging

import typer
from rich.markup import escape

from chico.cli.output import get_console, get_err_console, run_with_progress
from chico.core.config import ConfigNotFoundError, ConfigValidationError, load_config
from chico.core.plan import compute_plan
from chico.core.resource import ChangeType

logger = logging.getLogger("chico")

_PLAN_MESSAGES: list[str] = [
    "🔍  Fetching desired state...",
    "🛰️  Reaching out to sources...",
    "🧮  Computing differences...",
    "⚙️  Analyzing changes...",
    "🔎  Almost there...",
]

_CHANGE_SYMBOL: dict[str, str] = {
    ChangeType.ADD: "[green]+[/green]",
    ChangeType.MODIFY: "[yellow]~[/yellow]",
    ChangeType.REMOVE: "[red]-[/red]",
}


def plan(source: str | None = None) -> None:
    """Compute the changeset between desired and current state.

    Fetches desired state from every configured source (or a single source
    when ``source`` is given), diffs it against the current local state,
    and prints a summary of what would change. Nothing is written to disk.

    Parameters
    ----------
    source:
        Optional source name to scope the plan to. When ``None``, all
        sources are planned.
    """
    logger.info("plan.started", extra={"source_filter": source})

    try:
        config = load_config()
        if source:
            config = config.filter_by_source(source)
    except (ConfigNotFoundError, ConfigValidationError) as exc:
        get_err_console().print(f"[bold red]Error:[/bold red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    console = get_console()

    try:
        result = run_with_progress(
            console, _PLAN_MESSAGES, lambda: compute_plan(config)
        )
    except Exception as exc:
        logger.error("plan.failed", extra={"error": str(exc)})
        get_err_console().print(f"[bold red]Error:[/bold red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    logger.info(
        "plan.completed",
        extra={"plan_id": result.plan_id, "changes": len(result.changes)},
    )

    if not result.has_changes:
        console.print("[dim]No changes. Your configuration is up to date.[/dim]")
        return

    console.print(
        f"[bold]Plan:[/bold] {len(result.changes)} change(s)"
        f"  ([dim]risk: {escape(str(result.risk_level))}[/dim])\n"
    )
    for diff in result.changes:
        symbol = _CHANGE_SYMBOL.get(diff.change_type, "?")
        console.print(f"  {symbol} {escape(diff.resource_id)}")

    console.print(f"\n[dim]Plan ID:[/dim] {escape(result.plan_id)}")
