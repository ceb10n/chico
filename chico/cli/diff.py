"""Implementation of the ``chico diff`` command.

Shows the field-level differences between desired state (from sources) and
current local state, without writing anything to disk.
"""

from __future__ import annotations

import logging

import typer
from rich.markup import escape

from chico.cli.output import get_console, get_err_console
from chico.core.config import ConfigNotFoundError, ConfigValidationError, load_config
from chico.core.plan import compute_plan
from chico.core.resource import ChangeType

logger = logging.getLogger("chico")

_CHANGE_SYMBOL: dict[str, str] = {
    ChangeType.ADD: "[green]+[/green]",
    ChangeType.MODIFY: "[yellow]~[/yellow]",
    ChangeType.REMOVE: "[red]-[/red]",
}

_TRUNCATE_AT = 60


def _truncate(value: object) -> str:
    """Return a short string representation of *value*, truncated if needed."""
    text = str(value)
    if len(text) <= _TRUNCATE_AT:
        return text
    return text[:_TRUNCATE_AT] + "..."


def diff(source: str | None = None) -> None:
    """Show field-level differences between desired and current state.

    Parameters
    ----------
    source:
        Optional source name to scope the diff to. When ``None``, all
        sources are diffed.
    """
    logger.info("diff.started", extra={"source_filter": source})

    try:
        config = load_config()
        if source:
            config = config.filter_by_source(source)
    except (ConfigNotFoundError, ConfigValidationError) as exc:
        get_err_console().print(f"[bold red]Error:[/bold red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    try:
        result = compute_plan(config)
    except Exception as exc:
        logger.error("diff.failed", extra={"error": str(exc)})
        get_err_console().print(f"[bold red]Error:[/bold red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    logger.info("diff.completed", extra={"changes": len(result.changes)})

    console = get_console()

    if not result.has_changes:
        console.print("[dim]No changes. Your configuration is up to date.[/dim]")
        return

    console.print(f"[bold]Diff:[/bold] {len(result.changes)} change(s)\n")
    for d in result.changes:
        symbol = _CHANGE_SYMBOL.get(d.change_type, "?")
        console.print(f"  {symbol} {escape(d.resource_id)}")
        for field_name, field_change in d.changes.items():
            from_str = escape(_truncate(field_change.from_value))
            to_str = escape(_truncate(field_change.to_value))
            console.print(
                f"    [dim]{escape(field_name)}:[/dim]"
                f" [red]{from_str!r}[/red] [dim]→[/dim] [green]{to_str!r}[/green]"
            )
