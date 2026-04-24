"""Scheduler backends for chico."""

from __future__ import annotations

import sys


def get_scheduler():
    """Return the platform-appropriate scheduler module.

    Returns the Windows Task Scheduler backend on Windows and the
    cron backend on macOS and Linux.
    """
    if sys.platform == "win32":
        from chico.schedulers import windows

        return windows
    from chico.schedulers import unix

    return unix
