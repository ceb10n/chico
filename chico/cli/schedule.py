"""Implementation of the ``chico schedule`` command group.

Manages a recurring OS-level task that runs ``chico sync`` automatically.
Currently supports Windows Task Scheduler; other platforms will be added
in a future release.
"""

from __future__ import annotations

import logging

import typer

from chico.schedulers.windows import (
    _STATUS_FIELDS,
    SchedulerError,
    install,
    is_installed,
    query,
    uninstall,
)

logger = logging.getLogger("chico")

schedule_app = typer.Typer(
    name="schedule",
    help="Manage the periodic sync schedule (Windows Task Scheduler).",
    no_args_is_help=True,
)


@schedule_app.command("install")
def install_cmd(
    every: int = typer.Option(30, "--every", help="Run interval in minutes (1–1439)."),
) -> None:
    """Install a scheduled task that runs ``chico sync`` automatically."""
    try:
        install(every)
    except SchedulerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        logger.error("schedule.install.failed", extra={"error": str(exc)})
        raise typer.Exit(1) from exc

    typer.echo(f"Scheduled chico sync every {every} minute(s).")
    typer.echo("  Task name: ChicoSync")
    typer.echo(f"  Command:   {__import__('sys').executable} -m chico sync")
    logger.info("schedule.install.completed", extra={"interval_minutes": every})


@schedule_app.command("uninstall")
def uninstall_cmd() -> None:
    """Remove the ChicoSync scheduled task."""
    try:
        uninstall()
    except SchedulerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        logger.error("schedule.uninstall.failed", extra={"error": str(exc)})
        raise typer.Exit(1) from exc

    typer.echo("Scheduled task removed.")
    logger.info("schedule.uninstall.completed")


@schedule_app.command("status")
def status_cmd() -> None:
    """Show whether the ChicoSync scheduled task is installed."""
    if not is_installed():
        typer.echo(
            "No scheduled task found. Run `chico schedule install` to set one up."
        )
        return

    info = query()
    typer.echo("ChicoSync is installed.\n")

    if info:
        for field in _STATUS_FIELDS:
            if field in info:
                typer.echo(f"  {field}: {info[field]}")
