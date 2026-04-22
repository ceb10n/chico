"""Windows Task Scheduler backend for chico.

Uses ``schtasks.exe`` to create, remove, and query a recurring task that
runs ``chico sync`` automatically.

Example usage::

    from chico.schedulers.windows import install, uninstall, is_installed, query

    install(interval_minutes=30)
    print(is_installed())   # True
    print(query())          # {"Status": "Ready", "Last Run Time": "...", ...}
    uninstall()
"""

from __future__ import annotations

import re
import subprocess
import sys

TASK_NAME = "ChicoSync"

_STATUS_FIELDS = (
    "Status",
    "Last Run Time",
    "Last Result",
    "Next Run Time",
    "Repeat: Every",
    "Task To Run",
)


class SchedulerError(Exception):
    """Raised when a Task Scheduler operation fails."""


def install(interval_minutes: int) -> None:
    """Create or update the ChicoSync scheduled task.

    Schedules ``python -m chico sync`` to run every ``interval_minutes``
    minutes for the current user. Safe to call when the task already exists
    — the ``/F`` flag silently overwrites it.

    Parameters
    ----------
    interval_minutes:
        How often to run, in minutes. Must be between 1 and 1439.

    Raises
    ------
    SchedulerError
        If ``schtasks`` exits with a non-zero return code.
    """
    if not 1 <= interval_minutes <= 1439:
        raise SchedulerError(
            f"interval_minutes must be between 1 and 1439, got {interval_minutes}"
        )

    cmd = f'"{sys.executable}" -m chico sync'
    result = _run(
        "/Create",
        "/TN",
        TASK_NAME,
        "/TR",
        cmd,
        "/SC",
        "MINUTE",
        "/MO",
        str(interval_minutes),
        "/F",
    )
    if result.returncode != 0:
        raise SchedulerError(result.stderr.strip() or result.stdout.strip())


def uninstall() -> None:
    """Delete the ChicoSync scheduled task.

    Raises
    ------
    SchedulerError
        If ``schtasks`` exits with a non-zero return code.
    """
    result = _run("/Delete", "/TN", TASK_NAME, "/F")
    if result.returncode != 0:
        raise SchedulerError(result.stderr.strip() or result.stdout.strip())


def is_installed() -> bool:
    """Return ``True`` if the ChicoSync task exists in Task Scheduler."""
    return _run("/Query", "/TN", TASK_NAME).returncode == 0


def query() -> dict[str, str] | None:
    """Return key fields from the ChicoSync task, or ``None`` if not installed.

    Parses the ``schtasks /Query /FO LIST /V`` output into a dict. Only the
    fields listed in :data:`_STATUS_FIELDS` are included.
    """
    result = _run("/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V")
    if result.returncode != 0:
        return None

    data: dict[str, str] = {}
    for line in result.stdout.splitlines():
        match = re.match(r"^(.+?):\s{2,}(.*)$", line)
        if match:
            key = match.group(1).strip()
            if key in _STATUS_FIELDS:
                data[key] = match.group(2).strip()
    return data


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a ``schtasks`` command and return the result."""
    return subprocess.run(
        ["schtasks", *args],
        capture_output=True,
        text=True,
    )
