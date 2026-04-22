"""Tests for chico.cli.schedule (chico schedule subcommands)."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from chico.cli.main import app
from chico.core.log import _LOGGER_NAME
from chico.schedulers.windows import SchedulerError

runner = CliRunner()


@pytest.fixture(autouse=True)
def reset_chico_logger():
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    yield
    logger.handlers.clear()


# ── schedule install ──────────────────────────────────────────────────────────


class TestScheduleInstall:
    def test_exits_cleanly_on_success(self):
        with patch("chico.cli.schedule.install"):
            result = runner.invoke(app, ["schedule", "install"])
        assert result.exit_code == 0

    def test_shows_confirmation_message(self):
        with patch("chico.cli.schedule.install"):
            result = runner.invoke(app, ["schedule", "install"])
        assert "Scheduled chico sync" in result.output

    def test_uses_default_interval_of_30(self):
        with patch("chico.cli.schedule.install") as mock_install:
            runner.invoke(app, ["schedule", "install"])
        mock_install.assert_called_once_with(30)

    def test_accepts_custom_interval(self):
        with patch("chico.cli.schedule.install") as mock_install:
            runner.invoke(app, ["schedule", "install", "--every", "60"])
        mock_install.assert_called_once_with(60)

    def test_shows_task_name_in_output(self):
        with patch("chico.cli.schedule.install"):
            result = runner.invoke(app, ["schedule", "install"])
        assert "ChicoSync" in result.output

    def test_exits_with_error_on_failure(self):
        with patch(
            "chico.cli.schedule.install", side_effect=SchedulerError("Access denied")
        ):
            result = runner.invoke(app, ["schedule", "install"])
        assert result.exit_code == 1

    def test_shows_error_message_on_failure(self):
        with patch(
            "chico.cli.schedule.install", side_effect=SchedulerError("Access denied")
        ):
            result = runner.invoke(app, ["schedule", "install"])
        assert "Access denied" in result.output


# ── schedule uninstall ────────────────────────────────────────────────────────


class TestScheduleUninstall:
    def test_exits_cleanly_on_success(self):
        with patch("chico.cli.schedule.uninstall"):
            result = runner.invoke(app, ["schedule", "uninstall"])
        assert result.exit_code == 0

    def test_shows_confirmation_message(self):
        with patch("chico.cli.schedule.uninstall"):
            result = runner.invoke(app, ["schedule", "uninstall"])
        assert "removed" in result.output

    def test_exits_with_error_on_failure(self):
        with patch(
            "chico.cli.schedule.uninstall",
            side_effect=SchedulerError("Task not found"),
        ):
            result = runner.invoke(app, ["schedule", "uninstall"])
        assert result.exit_code == 1

    def test_shows_error_message_on_failure(self):
        with patch(
            "chico.cli.schedule.uninstall",
            side_effect=SchedulerError("Task not found"),
        ):
            result = runner.invoke(app, ["schedule", "uninstall"])
        assert "Task not found" in result.output


# ── schedule status ───────────────────────────────────────────────────────────


class TestScheduleStatus:
    def test_shows_not_installed_message(self):
        with patch("chico.cli.schedule.is_installed", return_value=False):
            result = runner.invoke(app, ["schedule", "status"])
        assert "No scheduled task" in result.output

    def test_exits_cleanly_when_not_installed(self):
        with patch("chico.cli.schedule.is_installed", return_value=False):
            result = runner.invoke(app, ["schedule", "status"])
        assert result.exit_code == 0

    def test_shows_installed_message(self):
        with (
            patch("chico.cli.schedule.is_installed", return_value=True),
            patch("chico.cli.schedule.query", return_value={}),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert "installed" in result.output.lower()

    def test_shows_status_field(self):
        with (
            patch("chico.cli.schedule.is_installed", return_value=True),
            patch("chico.cli.schedule.query", return_value={"Status": "Ready"}),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert "Ready" in result.output

    def test_shows_repeat_every_field(self):
        with (
            patch("chico.cli.schedule.is_installed", return_value=True),
            patch(
                "chico.cli.schedule.query",
                return_value={"Repeat: Every": "0 Hour(s), 30 Minute(s)"},
            ),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert "30 Minute(s)" in result.output

    def test_handles_none_query_result(self):
        with (
            patch("chico.cli.schedule.is_installed", return_value=True),
            patch("chico.cli.schedule.query", return_value=None),
        ):
            result = runner.invoke(app, ["schedule", "status"])
        assert result.exit_code == 0
        assert "installed" in result.output.lower()
