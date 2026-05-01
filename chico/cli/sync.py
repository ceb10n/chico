"""Implementation of the ``chico sync`` command.

Combines plan and apply in a single step: fetches desired state, shows what
would change, then immediately applies it.
"""

from __future__ import annotations

import logging

import typer
from rich.markup import escape

from chico.cli.output import get_console, get_err_console
from chico.core.apply import execute_apply
from chico.core.config import ConfigNotFoundError, ConfigValidationError, load_config
from chico.core.resource import ChangeType, ResultStatus

logger = logging.getLogger("chico")

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


def sync(source: str | None = None) -> None:
    """Fetch desired state and apply all changes in one step.

    Parameters
    ----------
    source:
        Optional source name to scope the sync to. When ``None``, all
        sources are synced.
    """
    logger.info("sync.started", extra={"source_filter": source})

    try:
        config = load_config()
        if source:
            config = config.filter_by_source(source)
    except (ConfigNotFoundError, ConfigValidationError) as exc:
        get_err_console().print(f"[bold red]Error:[/bold red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    try:
        result = execute_apply(config)
    except Exception as exc:
        logger.error("sync.failed", extra={"error": str(exc)})
        get_err_console().print(f"[bold red]Error:[/bold red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    console = get_console()

    if not result.plan.has_changes:
        console.print("[dim]Nothing to sync. Your configuration is up to date.[/dim]")
        logger.info("sync.completed", extra={"applied": 0, "errors": 0})
        return

    console.print(f"Syncing [bold]{len(result.plan.changes)}[/bold] change(s)...\n")

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
            f"Synced [bold]{result.ok_count}[/bold],"
            f" [bold red]{result.error_count}[/bold red] error(s)."
        )
        logger.info(
            "sync.completed",
            extra={"applied": result.ok_count, "errors": result.error_count},
        )
        raise typer.Exit(1)

    console.print(f"[green]Synced {result.ok_count} change(s). No errors.[/green]")
    logger.info("sync.completed", extra={"applied": result.ok_count, "errors": 0})
