"""Tests for chico.schedulers.windows."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from chico.schedulers.windows import (
    TASK_NAME,
    SchedulerError,
    install,
    is_installed,
    query,
    uninstall,
)


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ── install ───────────────────────────────────────────────────────────────────


class TestInstall:
    def test_calls_schtasks_create(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)) as mock:
            install(30)
        args = mock.call_args[0]
        assert "/Create" in args
        assert "/TN" in args
        assert TASK_NAME in args

    def test_passes_interval_to_schtasks(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)) as mock:
            install(60)
        args = mock.call_args[0]
        assert "/MO" in args
        assert "60" in args

    def test_schedules_per_minute(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)) as mock:
            install(15)
        args = mock.call_args[0]
        assert "/SC" in args
        assert "MINUTE" in args

    def test_uses_force_flag(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)) as mock:
            install(30)
        assert "/F" in mock.call_args[0]

    def test_raises_on_schtasks_failure(self):
        with (
            patch(
                "chico.schedulers.windows._run",
                return_value=_completed(1, stderr="Access denied."),
            ),
            pytest.raises(SchedulerError, match="Access denied"),
        ):
            install(30)

    def test_raises_on_stdout_error_when_stderr_empty(self):
        with (
            patch(
                "chico.schedulers.windows._run",
                return_value=_completed(1, stdout="ERROR: Something went wrong."),
            ),
            pytest.raises(SchedulerError, match="Something went wrong"),
        ):
            install(30)

    def test_raises_on_interval_below_minimum(self):
        with pytest.raises(SchedulerError, match="1 and 1439"):
            install(0)

    def test_raises_on_interval_above_maximum(self):
        with pytest.raises(SchedulerError, match="1 and 1439"):
            install(1440)

    def test_accepts_minimum_interval(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)):
            install(1)

    def test_accepts_maximum_interval(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)):
            install(1439)

    def test_command_includes_python_executable(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)) as mock:
            install(30)
        args = mock.call_args[0]
        tr_index = list(args).index("/TR")
        cmd = args[tr_index + 1]
        assert "-m chico sync" in cmd


# ── uninstall ─────────────────────────────────────────────────────────────────


class TestUninstall:
    def test_calls_schtasks_delete(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)) as mock:
            uninstall()
        args = mock.call_args[0]
        assert "/Delete" in args
        assert TASK_NAME in args

    def test_uses_force_flag(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)) as mock:
            uninstall()
        assert "/F" in mock.call_args[0]

    def test_raises_on_failure(self):
        with (
            patch(
                "chico.schedulers.windows._run",
                return_value=_completed(1, stderr="Task not found."),
            ),
            pytest.raises(SchedulerError, match="Task not found"),
        ):
            uninstall()


# ── is_installed ──────────────────────────────────────────────────────────────


class TestIsInstalled:
    def test_returns_true_when_task_exists(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(0)):
            assert is_installed() is True

    def test_returns_false_when_task_missing(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(1)):
            assert is_installed() is False


# ── query ─────────────────────────────────────────────────────────────────────


_SCHTASKS_LIST_OUTPUT = """\
HostName:                             HOSTNAME
TaskName:                             \\ChicoSync
Next Run Time:                        1/1/2025 12:30:00 AM
Status:                               Ready
Last Run Time:                        1/1/2025 12:00:00 AM
Last Result:                          0
Task To Run:                          "python.exe" -m chico sync
Repeat: Every:                        0 Hour(s), 30 Minute(s)
"""


class TestQuery:
    def test_returns_none_when_task_not_found(self):
        with patch("chico.schedulers.windows._run", return_value=_completed(1)):
            assert query() is None

    def test_returns_status_field(self):
        with patch(
            "chico.schedulers.windows._run",
            return_value=_completed(0, stdout=_SCHTASKS_LIST_OUTPUT),
        ):
            result = query()
        assert result is not None
        assert result["Status"] == "Ready"

    def test_returns_last_run_time(self):
        with patch(
            "chico.schedulers.windows._run",
            return_value=_completed(0, stdout=_SCHTASKS_LIST_OUTPUT),
        ):
            result = query()
        assert result is not None
        assert "12:00:00 AM" in result["Last Run Time"]

    def test_returns_repeat_every(self):
        with patch(
            "chico.schedulers.windows._run",
            return_value=_completed(0, stdout=_SCHTASKS_LIST_OUTPUT),
        ):
            result = query()
        assert result is not None
        assert result["Repeat: Every"] == "0 Hour(s), 30 Minute(s)"

    def test_returns_task_to_run(self):
        with patch(
            "chico.schedulers.windows._run",
            return_value=_completed(0, stdout=_SCHTASKS_LIST_OUTPUT),
        ):
            result = query()
        assert result is not None
        assert "chico sync" in result["Task To Run"]

    def test_excludes_unlisted_fields(self):
        with patch(
            "chico.schedulers.windows._run",
            return_value=_completed(0, stdout=_SCHTASKS_LIST_OUTPUT),
        ):
            result = query()
        assert result is not None
        assert "HostName" not in result
        assert "TaskName" not in result

    def test_returns_empty_dict_on_blank_output(self):
        with patch(
            "chico.schedulers.windows._run",
            return_value=_completed(0, stdout=""),
        ):
            result = query()
        assert result == {}

    def test_skips_lines_without_key_value_pattern(self):
        output = "This line has no double-space separator\nStatus:                               Ready\n"
        with patch(
            "chico.schedulers.windows._run",
            return_value=_completed(0, stdout=output),
        ):
            result = query()
        assert result == {"Status": "Ready"}


# ── _run ──────────────────────────────────────────────────────────────────────


class TestRun:
    def test_invokes_schtasks_with_args(self):
        with patch(
            "chico.schedulers.windows.subprocess.run", return_value=_completed(0)
        ) as mock:
            from chico.schedulers.windows import _run

            _run("/Query", "/TN", "ChicoSync")
        mock.assert_called_once_with(
            ["schtasks", "/Query", "/TN", "ChicoSync"],
            capture_output=True,
            text=True,
        )
