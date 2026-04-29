"""Implementation of the ``chico plan`` command.

Computes the changeset between desired state (from sources) and current local
state (on disk), then prints a human-readable summary.
"""

from __future__ import annotations

import logging

import typer

from chico.core.config import ConfigNotFoundError, ConfigValidationError, load_config
from chico.core.plan import compute_plan
from chico.core.resource import ChangeType

logger = logging.getLogger("chico")

_CHANGE_SYMBOL: dict[str, str] = {
    ChangeType.ADD: "+",
    ChangeType.MODIFY: "~",
    ChangeType.REMOVE: "-",
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
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    try:
        result = compute_plan(config)
    except Exception as exc:
        logger.error("plan.failed", extra={"error": str(exc)})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    logger.info(
        "plan.completed",
        extra={"plan_id": result.plan_id, "changes": len(result.changes)},
    )

    if not result.has_changes:
        typer.echo("No changes. Your configuration is up to date.")
        return

    typer.echo(f"Plan: {len(result.changes)} change(s)  (risk: {result.risk_level})\n")
    for diff in result.changes:
        symbol = _CHANGE_SYMBOL.get(diff.change_type, "?")
        typer.echo(f"  {symbol} {diff.resource_id}")

    typer.echo(f"\nPlan ID: {result.plan_id}")
