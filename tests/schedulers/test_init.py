"""Tests for chico.schedulers.get_scheduler."""

from __future__ import annotations

from unittest.mock import patch

from chico.schedulers import get_scheduler


class TestGetScheduler:
    def test_returns_windows_scheduler_on_windows(self):
        with patch("chico.schedulers.sys.platform", "win32"):
            sched = get_scheduler()
        from chico.schedulers import windows

        assert sched is windows

    def test_returns_unix_scheduler_on_linux(self):
        with patch("chico.schedulers.sys.platform", "linux"):
            sched = get_scheduler()
        from chico.schedulers import unix

        assert sched is unix

    def test_returns_unix_scheduler_on_darwin(self):
        with patch("chico.schedulers.sys.platform", "darwin"):
            sched = get_scheduler()
        from chico.schedulers import unix

        assert sched is unix
