"""Implementation of the ``chico schedule`` command group.

Manages a recurring OS-level task that runs ``chico sync`` automatically.
Uses Windows Task Scheduler on Windows and cron on macOS/Linux.
"""

from __future__ import annotations

import logging
import sys

import typer

from chico.schedulers import get_scheduler

logger = logging.getLogger("chico")

schedule_app = typer.Typer(
    name="schedule",
    help="Automatically sync on a schedule — no manual runs needed.",
    no_args_is_help=True,
)


@schedule_app.command("install")
def install_cmd(
    every: int = typer.Option(30, "--every", help="How often to sync, in minutes."),
) -> None:
    """Run chico-ai sync automatically on a schedule.

    Uses cron on macOS and Linux, and Windows Task Scheduler on Windows.
    Default interval is every 30 minutes. Pass --every to change it.
    """
    sched = get_scheduler()
    try:
        sched.install(every)
    except sched.SchedulerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        logger.error("schedule.install.failed", extra={"error": str(exc)})
        raise typer.Exit(1) from exc

    typer.echo(f"Scheduled chico sync every {every} minute(s).")
    typer.echo(f"  Command: {sys.executable} -m chico sync")
    logger.info("schedule.install.completed", extra={"interval_minutes": every})


@schedule_app.command("uninstall")
def uninstall_cmd() -> None:
    """Stop automatic syncing by removing the scheduled task."""
    sched = get_scheduler()
    try:
        sched.uninstall()
    except sched.SchedulerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        logger.error("schedule.uninstall.failed", extra={"error": str(exc)})
        raise typer.Exit(1) from exc

    typer.echo("Scheduled task removed.")
    logger.info("schedule.uninstall.completed")


@schedule_app.command("status")
def status_cmd() -> None:
    """Show whether automatic syncing is active and its current interval."""
    sched = get_scheduler()
    if not sched.is_installed():
        typer.echo(
            "No scheduled task found. Run `chico schedule install` to set one up."
        )
        return

    info = sched.query()
    typer.echo("ChicoSync is installed.\n")

    if info:
        for key, value in info.items():
            typer.echo(f"  {key}: {value}")
