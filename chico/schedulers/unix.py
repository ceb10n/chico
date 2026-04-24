"""Unix cron scheduler backend for chico.

Uses ``crontab`` to install, remove, and query a recurring entry that
runs ``chico sync`` automatically on macOS and Linux.

Supports intervals of 1–59 minutes (the cron minute field range). For
longer intervals use the Windows Task Scheduler backend instead.

Example usage::

    from chico.schedulers.unix import install, uninstall, is_installed, query

    install(interval_minutes=30)
    print(is_installed())   # True
    print(query())          # {"Schedule": "*/30 * * * *", "Command": "..."}
    uninstall()
"""

from __future__ import annotations

import subprocess
import sys

CRON_MARKER = "# chico-sync"


class SchedulerError(Exception):
    """Raised when a cron operation fails."""


def install(interval_minutes: int) -> None:
    """Add or update the chico sync cron entry.

    Removes any existing chico entry before adding the new one, so this
    is safe to call repeatedly or to change the interval.

    Parameters
    ----------
    interval_minutes:
        How often to run, in minutes. Must be between 1 and 59.

    Raises
    ------
    SchedulerError
        If the interval is out of range or ``crontab`` exits non-zero.
    """
    if not 1 <= interval_minutes <= 59:
        raise SchedulerError(
            f"interval_minutes must be between 1 and 59 on Unix, got {interval_minutes}"
        )

    lines = [line for line in _crontab_lines() if CRON_MARKER not in line]
    cmd = f"{sys.executable} -m chico sync"
    lines.append(f"*/{interval_minutes} * * * * {cmd}  {CRON_MARKER}")
    _write_crontab(lines)


def uninstall() -> None:
    """Remove the chico sync cron entry.

    Raises
    ------
    SchedulerError
        If no chico entry exists or ``crontab`` exits non-zero.
    """
    lines = _crontab_lines()
    new_lines = [line for line in lines if CRON_MARKER not in line]
    if len(new_lines) == len(lines):
        raise SchedulerError("No chico scheduled task found.")
    _write_crontab(new_lines)


def is_installed() -> bool:
    """Return ``True`` if a chico sync cron entry exists."""
    return any(CRON_MARKER in line for line in _crontab_lines())


def query() -> dict[str, str] | None:
    """Return the schedule and command from the chico cron entry.

    Returns ``None`` if no entry is installed.
    """
    for line in _crontab_lines():
        if CRON_MARKER not in line:
            continue
        entry = line.replace(CRON_MARKER, "").strip()
        parts = entry.split(None, 5)
        schedule = " ".join(parts[:5]) if len(parts) >= 5 else entry
        command = parts[5].strip() if len(parts) > 5 else ""
        return {"Schedule": schedule, "Command": command}
    return None


def _crontab_lines() -> list[str]:
    """Return the current crontab as a list of lines.

    Returns an empty list when no crontab exists for the current user.
    """
    result = _run("-l")
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()


def _write_crontab(lines: list[str]) -> None:
    """Write ``lines`` as the new crontab."""
    content = "\n".join(lines) + "\n"
    result = _run("-", stdin_input=content)
    if result.returncode != 0:
        raise SchedulerError(result.stderr.strip() or result.stdout.strip())


def _run(
    *args: str, stdin_input: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a ``crontab`` command and return the result."""
    return subprocess.run(
        ["crontab", *args],
        input=stdin_input,
        capture_output=True,
        text=True,
    )
