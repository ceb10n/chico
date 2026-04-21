"""Implementation of the ``chico diff`` command.

Shows the field-level differences between desired state (from sources) and
current local state, without writing anything to disk.
"""

from __future__ import annotations

import logging

import typer

from chico.core.config import ConfigNotFoundError, load_config
from chico.core.plan import compute_plan
from chico.core.resource import ChangeType

logger = logging.getLogger("chico")

_CHANGE_SYMBOL: dict[str, str] = {
    ChangeType.ADD: "+",
    ChangeType.MODIFY: "~",
    ChangeType.REMOVE: "-",
}

_TRUNCATE_AT = 60


def _truncate(value: object) -> str:
    """Return a short string representation of *value*, truncated if needed."""
    text = str(value)
    if len(text) <= _TRUNCATE_AT:
        return text
    return text[:_TRUNCATE_AT] + "..."


def diff() -> None:
    """Show field-level differences between desired and current state.

    Fetches desired state from every configured source, diffs it against
    the current local state, and prints a detailed breakdown of what would
    change. For modified resources, the before and after value of each
    changed field is shown. Nothing is written to disk.
    """
    logger.info("diff.started")

    try:
        config = load_config()
    except ConfigNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    try:
        result = compute_plan(config)
    except Exception as exc:
        logger.error("diff.failed", extra={"error": str(exc)})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    logger.info("diff.completed", extra={"changes": len(result.changes)})

    if not result.has_changes:
        typer.echo("No changes. Your configuration is up to date.")
        return

    typer.echo(f"Diff: {len(result.changes)} change(s)\n")
    for d in result.changes:
        symbol = _CHANGE_SYMBOL.get(d.change_type, "?")
        typer.echo(f"  {symbol} {d.resource_id}")
        for field_name, field_change in d.changes.items():
            from_str = _truncate(field_change.from_value)
            to_str = _truncate(field_change.to_value)
            typer.echo(f"    {field_name}: {from_str!r} → {to_str!r}")
