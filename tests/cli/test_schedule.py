"""Tests for chico.cli.schedule (chico schedule subcommands)."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from chico.cli.main import app
from chico.core.log import _LOGGER_NAME

runner = CliRunner()


class _SchedulerError(Exception):
    pass


def _make_scheduler(
    install=None,
    uninstall=None,
    is_installed=True,
    query_result=None,
    install_error=None,
    uninstall_error=None,
) -> MagicMock:
    sched = MagicMock()
    sched.SchedulerError = _SchedulerError

    if install_error:
        sched.install.side_effect = install_error
    elif install is not None:
        sched.install.return_value = install

    if uninstall_error:
        sched.uninstall.side_effect = uninstall_error

    sched.is_installed.return_value = is_installed
    sched.query.return_value = query_result
    return sched


@pytest.fixture(autouse=True)
def reset_chico_logger():
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    yield
    logger.handlers.clear()


# ── schedule install ──────────────────────────────────────────────────────────


class TestScheduleInstall:
    def test_exits_cleanly_on_success(self):
        with patch("chico.cli.schedule.get_scheduler", return_value=_make_scheduler()):
            result = runner.invoke(app, ["schedule", "install"])
        assert result.exit_code == 0

    def test_shows_confirmation_message(self):
        with patch("chico.cli.schedule.get_scheduler", return_value=_make_scheduler()):
            result = runner.invoke(app, ["schedule", "install"])
        assert "Scheduled chico sync" in result.output

    def test_uses_default_interval_of_30(self):
        sched = _make_scheduler()
        with patch("chico.cli.schedule.get_scheduler", return_value=sched):
            runner.invoke(app, ["schedule", "install"])
        sched.install.assert_called_once_with(30)

    def test_accepts_custom_interval(self):
        sched = _make_scheduler()
        with patch("chico.cli.schedule.get_scheduler", return_value=sched):
            runner.invoke(app, ["schedule", "install", "--every", "15"])
        sched.install.assert_called_once_with(15)

    def test_exits_with_error_on_failure(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(
                install_error=_SchedulerError("Access denied")
            ),
        ):
            result = runner.invoke(app, ["schedule", "install"])
        assert result.exit_code == 1

    def test_shows_error_message_on_failure(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(
                install_error=_SchedulerError("Access denied")
            ),
        ):
            result = runner.invoke(app, ["schedule", "install"])
        assert "Access denied" in result.output


# ── schedule uninstall ────────────────────────────────────────────────────────


class TestScheduleUninstall:
    def test_exits_cleanly_on_success(self):
        with patch("chico.cli.schedule.get_scheduler", return_value=_make_scheduler()):
            result = runner.invoke(app, ["schedule", "uninstall"])
        assert result.exit_code == 0

    def test_shows_confirmation_message(self):
        with patch("chico.cli.schedule.get_scheduler", return_value=_make_scheduler()):
            result = runner.invoke(app, ["schedule", "uninstall"])
        assert "removed" in result.output

    def test_exits_with_error_on_failure(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(
                uninstall_error=_SchedulerError("Task not found")
            ),
        ):
            result = runner.invoke(app, ["schedule", "uninstall"])
        assert result.exit_code == 1

    def test_shows_error_message_on_failure(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(
                uninstall_error=_SchedulerError("Task not found")
            ),
        ):
            result = runner.invoke(app, ["schedule", "uninstall"])
        assert "Task not found" in result.output


# ── schedule status ───────────────────────────────────────────────────────────


class TestScheduleStatus:
    def test_shows_not_installed_message(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(is_installed=False),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert "No scheduled task" in result.output

    def test_exits_cleanly_when_not_installed(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(is_installed=False),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert result.exit_code == 0

    def test_shows_installed_message(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(query_result={}),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert "installed" in result.output.lower()

    def test_shows_query_fields(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(
                query_result={
                    "Schedule": "*/30 * * * *",
                    "Command": "python -m chico sync",
                }
            ),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert "*/30 * * * *" in result.output
        assert "python -m chico sync" in result.output

    def test_handles_none_query_result(self):
        with patch(
            "chico.cli.schedule.get_scheduler",
            return_value=_make_scheduler(query_result=None),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert result.exit_code == 0
        assert "installed" in result.output.lower()
