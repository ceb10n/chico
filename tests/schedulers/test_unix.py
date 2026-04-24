"""Tests for chico.schedulers.unix."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from chico.schedulers.unix import (
    CRON_MARKER,
    SchedulerError,
    _crontab_lines,
    _write_crontab,
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


_EXISTING_CRONTAB = (
    "0 9 * * 1 /usr/bin/backup.sh\n"
    f"*/30 * * * * /usr/bin/python3 -m chico sync  {CRON_MARKER}\n"
)

_EMPTY_CRONTAB = ""

_NO_CHICO_CRONTAB = "0 9 * * 1 /usr/bin/backup.sh\n"


# ── install ───────────────────────────────────────────────────────────────────


class TestInstall:
    def test_adds_cron_entry(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EMPTY_CRONTAB),
        ) as mock:
            install(30)
        write_call = [c for c in mock.call_args_list if c[0][0] == "-"]
        assert write_call, "expected a crontab write call"
        written = write_call[0][1]["stdin_input"]
        assert CRON_MARKER in written

    def test_includes_interval_in_cron_expression(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EMPTY_CRONTAB),
        ) as mock:
            install(15)
        write_call = [c for c in mock.call_args_list if c[0][0] == "-"]
        written = write_call[0][1]["stdin_input"]
        assert "*/15" in written

    def test_includes_chico_sync_command(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EMPTY_CRONTAB),
        ) as mock:
            install(30)
        write_call = [c for c in mock.call_args_list if c[0][0] == "-"]
        written = write_call[0][1]["stdin_input"]
        assert "-m chico sync" in written

    def test_replaces_existing_entry(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EXISTING_CRONTAB),
        ) as mock:
            install(15)
        write_call = [c for c in mock.call_args_list if c[0][0] == "-"]
        written = write_call[0][1]["stdin_input"]
        assert written.count(CRON_MARKER) == 1
        assert "*/15" in written

    def test_preserves_other_cron_entries(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_NO_CHICO_CRONTAB),
        ) as mock:
            install(30)
        write_call = [c for c in mock.call_args_list if c[0][0] == "-"]
        written = write_call[0][1]["stdin_input"]
        assert "/usr/bin/backup.sh" in written

    def test_raises_on_interval_below_minimum(self):
        with pytest.raises(SchedulerError, match="1 and 59"):
            install(0)

    def test_raises_on_interval_above_maximum(self):
        with pytest.raises(SchedulerError, match="1 and 59"):
            install(60)

    def test_accepts_minimum_interval(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EMPTY_CRONTAB),
        ):
            install(1)

    def test_accepts_maximum_interval(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EMPTY_CRONTAB),
        ):
            install(59)

    def test_raises_on_write_failure(self):
        def _side_effect(*args, **kwargs):
            if args[0] == "-":
                return _completed(1, stderr="crontab: not allowed")
            return _completed(0, stdout=_EMPTY_CRONTAB)

        with (
            patch("chico.schedulers.unix._run", side_effect=_side_effect),
            pytest.raises(SchedulerError, match="not allowed"),
        ):
            install(30)


# ── uninstall ─────────────────────────────────────────────────────────────────


class TestUninstall:
    def test_removes_chico_entry(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EXISTING_CRONTAB),
        ) as mock:
            uninstall()
        write_call = [c for c in mock.call_args_list if c[0][0] == "-"]
        written = write_call[0][1]["stdin_input"]
        assert CRON_MARKER not in written

    def test_preserves_other_entries(self):
        crontab = f"0 9 * * 1 /usr/bin/backup.sh\n*/30 * * * * python -m chico sync  {CRON_MARKER}\n"
        with patch(
            "chico.schedulers.unix._run", return_value=_completed(0, stdout=crontab)
        ) as mock:
            uninstall()
        write_call = [c for c in mock.call_args_list if c[0][0] == "-"]
        written = write_call[0][1]["stdin_input"]
        assert "/usr/bin/backup.sh" in written

    def test_raises_when_no_chico_entry(self):
        with (
            patch(
                "chico.schedulers.unix._run",
                return_value=_completed(0, stdout=_NO_CHICO_CRONTAB),
            ),
            pytest.raises(SchedulerError, match="No chico scheduled task found"),
        ):
            uninstall()

    def test_raises_on_write_failure(self):
        def _side_effect(*args, **kwargs):
            if args[0] == "-":
                return _completed(1, stderr="crontab: error")
            return _completed(0, stdout=_EXISTING_CRONTAB)

        with (
            patch("chico.schedulers.unix._run", side_effect=_side_effect),
            pytest.raises(SchedulerError, match="crontab: error"),
        ):
            uninstall()


# ── is_installed ──────────────────────────────────────────────────────────────


class TestIsInstalled:
    def test_returns_true_when_entry_exists(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EXISTING_CRONTAB),
        ):
            assert is_installed() is True

    def test_returns_false_when_no_entry(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_NO_CHICO_CRONTAB),
        ):
            assert is_installed() is False

    def test_returns_false_when_no_crontab(self):
        with patch("chico.schedulers.unix._run", return_value=_completed(1)):
            assert is_installed() is False


# ── query ─────────────────────────────────────────────────────────────────────


class TestQuery:
    def test_returns_none_when_not_installed(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_NO_CHICO_CRONTAB),
        ):
            assert query() is None

    def test_returns_schedule_field(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EXISTING_CRONTAB),
        ):
            result = query()
        assert result is not None
        assert result["Schedule"] == "*/30 * * * *"

    def test_returns_command_field(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout=_EXISTING_CRONTAB),
        ):
            result = query()
        assert result is not None
        assert "-m chico sync" in result["Command"]

    def test_returns_none_when_no_crontab(self):
        with patch("chico.schedulers.unix._run", return_value=_completed(1)):
            assert query() is None


# ── _crontab_lines ────────────────────────────────────────────────────────────


class TestCrontabLines:
    def test_returns_lines_from_crontab(self):
        with patch(
            "chico.schedulers.unix._run",
            return_value=_completed(0, stdout="line1\nline2\n"),
        ):
            assert _crontab_lines() == ["line1", "line2"]

    def test_returns_empty_list_when_no_crontab(self):
        with patch("chico.schedulers.unix._run", return_value=_completed(1)):
            assert _crontab_lines() == []


# ── _write_crontab ────────────────────────────────────────────────────────────


class TestWriteCrontab:
    def test_passes_content_as_stdin(self):
        with patch("chico.schedulers.unix._run", return_value=_completed(0)) as mock:
            _write_crontab(["line1", "line2"])
        assert mock.call_args[1]["stdin_input"] == "line1\nline2\n"

    def test_raises_on_failure_with_stderr(self):
        with (
            patch(
                "chico.schedulers.unix._run", return_value=_completed(1, stderr="oops")
            ),
            pytest.raises(SchedulerError, match="oops"),
        ):
            _write_crontab([])

    def test_raises_on_failure_with_stdout_when_stderr_empty(self):
        with (
            patch(
                "chico.schedulers.unix._run",
                return_value=_completed(1, stdout="stdout error"),
            ),
            pytest.raises(SchedulerError, match="stdout error"),
        ):
            _write_crontab([])


# ── _run ─────────────────────────────────────────────────────────────────────


class TestRun:
    def test_invokes_crontab_with_args(self):
        from chico.schedulers.unix import _run

        with patch(
            "chico.schedulers.unix.subprocess.run", return_value=_completed(0)
        ) as mock:
            _run("-l")
        mock.assert_called_once_with(
            ["crontab", "-l"],
            input=None,
            capture_output=True,
            text=True,
        )

    def test_passes_stdin_input(self):
        from chico.schedulers.unix import _run

        with patch(
            "chico.schedulers.unix.subprocess.run", return_value=_completed(0)
        ) as mock:
            _run("-", stdin_input="content\n")
        mock.assert_called_once_with(
            ["crontab", "-"],
            input="content\n",
            capture_output=True,
            text=True,
        )
