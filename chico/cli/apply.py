"""Implementation of the ``chico apply`` command.

Fetches desired state from all configured sources, applies every change to
the local Kiro directory, and writes the outcome to ``~/.chico/state.json``.
"""

from __future__ import annotations

import logging

import typer

from chico.core.apply import execute_apply
from chico.core.config import ConfigNotFoundError, ConfigValidationError, load_config
from chico.core.resource import ChangeType, ResultStatus

logger = logging.getLogger("chico")

_CHANGE_SYMBOL: dict[str, str] = {
    ChangeType.ADD: "+",
    ChangeType.MODIFY: "~",
    ChangeType.REMOVE: "-",
}

_STATUS_LABEL: dict[str, str] = {
    ResultStatus.OK: "ok",
    ResultStatus.ERROR: "error",
    ResultStatus.SKIPPED: "skipped",
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
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    try:
        result = execute_apply(config)
    except Exception as exc:
        logger.error("apply.failed", extra={"error": str(exc)})
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    if not result.plan.has_changes:
        typer.echo("No changes. Your configuration is up to date.")
        logger.info("apply.completed", extra={"applied": 0, "errors": 0})
        return

    typer.echo(f"Applying {len(result.plan.changes)} change(s)...\n")

    change_by_id = {d.resource_id: d for d in result.plan.changes}
    for res in result.results:
        diff = change_by_id.get(res.resource_id)
        symbol = _CHANGE_SYMBOL.get(diff.change_type, "?") if diff else "?"
        label = _STATUS_LABEL.get(str(res.status), str(res.status))
        line = f"  {symbol} {res.resource_id}    {label}"
        if res.status == ResultStatus.ERROR and res.message:
            line += f": {res.message}"
        typer.echo(line)

    typer.echo("")

    if result.has_errors:
        typer.echo(f"Applied {result.ok_count}, {result.error_count} error(s).")
        logger.info(
            "apply.completed",
            extra={"applied": result.ok_count, "errors": result.error_count},
        )
        raise typer.Exit(1)

    typer.echo(f"Applied {result.ok_count} change(s). No errors.")
    logger.info(
        "apply.completed",
        extra={"applied": result.ok_count, "errors": 0},
    )
