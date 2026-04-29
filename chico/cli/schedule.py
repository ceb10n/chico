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


def _build_sync_command(source: str | None = None) -> str:
    """Build the shell command for the scheduled sync task."""
    base = f"{sys.executable} -m chico sync"
    if source:
        return f"{base} {source}"
    return base


@schedule_app.command("install")
def install_cmd(
    every: int = typer.Option(30, "--every", help="How often to sync, in minutes."),
    source: str | None = typer.Option(
        None, "--source", help="Source name to sync. Omit to sync all sources."
    ),
) -> None:
    """Run chico-ai sync automatically on a schedule.

    Uses cron on macOS and Linux, and Windows Task Scheduler on Windows.
    Default interval is every 30 minutes. Pass --every to change it.
    Pass --source to schedule only a specific source.
    """
    sched = get_scheduler()
    cmd = _build_sync_command(source)
    try:
        sched.install(every, command=cmd)
    except sched.SchedulerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        logger.error("schedule.install.failed", extra={"error": str(exc)})
        raise typer.Exit(1) from exc

    typer.echo(f"Scheduled chico sync every {every} minute(s).")
    typer.echo(f"  Command: {cmd}")
    logger.info(
        "schedule.install.completed",
        extra={"interval_minutes": every, "source": source},
    )


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
