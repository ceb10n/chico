"""Implementation of the ``chico apply`` command.

Fetches desired state from all configured sources, applies every change to
the local Kiro directory, and writes the outcome to ``~/.chico/state.json``.
"""

from __future__ import annotations

import logging

import typer
from rich.markup import escape

from chico.cli.output import get_console, get_err_console, run_with_progress
from chico.core.apply import execute_apply
from chico.core.config import ConfigNotFoundError, ConfigValidationError, load_config
from chico.core.resource import ChangeType, ResultStatus

logger = logging.getLogger("chico")

_APPLY_MESSAGES: list[str] = [
    "🚀  Applying changes...",
    "📦  Writing resources...",
    "🔧  Updating configuration...",
    "✍️  Almost done...",
    "⚡  Finishing up...",
]

_CHANGE_SYMBOL: dict[str, str] = {
    ChangeType.ADD: "[green]+[/green]",
    ChangeType.MODIFY: "[yellow]~[/yellow]",
    ChangeType.REMOVE: "[red]-[/red]",
}

_STATUS_LABEL: dict[str, str] = {
    ResultStatus.OK: "[green]ok[/green]",
    ResultStatus.ERROR: "[red]error[/red]",
    ResultStatus.SKIPPED: "[dim]skipped[/dim]",
}


def apply(source: str | None = None) -> None:
    """Apply the changeset between desired and current state.

    Parameters
    ----------
    source:
        Optional source name to scope the apply to. When ``None``, all
        sources are applied.
    """
    logger.info("apply.started", extra={"source_filter": source})

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
            console, _APPLY_MESSAGES, lambda: execute_apply(config)
        )
    except Exception as exc:
        logger.error("apply.failed", extra={"error": str(exc)})
        get_err_console().print(f"[bold red]Error:[/bold red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    if not result.plan.has_changes:
        console.print("[dim]No changes. Your configuration is up to date.[/dim]")
        logger.info("apply.completed", extra={"applied": 0, "errors": 0})
        return

    console.print(f"Applying [bold]{len(result.plan.changes)}[/bold] change(s)...\n")

    change_by_id = {d.resource_id: d for d in result.plan.changes}
    for res in result.results:
        diff = change_by_id.get(res.resource_id)
        symbol = _CHANGE_SYMBOL.get(diff.change_type, "?") if diff else "?"
        label = _STATUS_LABEL.get(str(res.status), escape(str(res.status)))
        line = f"  {symbol} {escape(res.resource_id)}    {label}"
        if res.status == ResultStatus.ERROR and res.message:
            line += f": {escape(res.message)}"
        console.print(line)

    console.print("")

    if result.has_errors:
        console.print(
            f"Applied [bold]{result.ok_count}[/bold],"
            f" [bold red]{result.error_count}[/bold red] error(s)."
        )
        logger.info(
            "apply.completed",
            extra={"applied": result.ok_count, "errors": result.error_count},
        )
        raise typer.Exit(1)

    console.print(f"[green]Applied {result.ok_count} change(s). No errors.[/green]")
    logger.info(
        "apply.completed",
        extra={"applied": result.ok_count, "errors": 0},
    )
