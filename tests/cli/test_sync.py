"""Tests for chico.cli.sync (chico sync command)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chico.cli.main import app
from chico.core.apply import ApplyResult
from chico.core.log import _LOGGER_NAME
from chico.core.plan import Plan, RiskLevel
from chico.core.resource import ChangeType, Diff, Result, ResultStatus
from chico.core.source import SourceFetchError

runner = CliRunner()


@pytest.fixture(autouse=True)
def reset_chico_logger():
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture()
def chico_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("chico.core.log.CHICO_DIR", tmp_path)
    monkeypatch.setattr("chico.core.log.LOG_FILE", tmp_path / "chico.log")
    return tmp_path


@pytest.fixture()
def config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("providers: []\nsources: []\npolicy:\n  strategy: safe\n")
    monkeypatch.setattr("chico.core.config.CONFIG_FILE", cfg)
    return cfg


def _empty_result() -> ApplyResult:
    return ApplyResult(
        plan=Plan(plan_id="test-id", changes=[], risk_level=RiskLevel.NONE),
        results=[],
    )


def _result_with_changes(ok: int = 1, errors: int = 0) -> ApplyResult:
    results = [
        Result(status=ResultStatus.OK, resource_id=f"/file-ok-{i}.md")
        for i in range(ok)
    ] + [
        Result(
            status=ResultStatus.ERROR,
            resource_id=f"/file-err-{i}.md",
            message="Permission denied",
        )
        for i in range(errors)
    ]
    changes = [
        Diff(change_type=ChangeType.ADD, resource_id=r.resource_id) for r in results
    ]
    return ApplyResult(
        plan=Plan(plan_id="plan-abc", changes=changes, risk_level=RiskLevel.LOW),
        results=results,
    )


# ── no config ─────────────────────────────────────────────────────────────────


class TestSyncNoConfig:
    def test_exits_with_error_when_no_config(self, chico_home, tmp_path, monkeypatch):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 1

    def test_shows_error_message_when_no_config(
        self, chico_home, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["sync"])
        assert "Config file not found" in result.output

    def test_exits_with_error_for_unknown_source(
        self, chico_home, config_file, monkeypatch
    ):
        result = runner.invoke(app, ["sync", "nonexistent"])
        assert result.exit_code == 1

    def test_shows_error_for_unknown_source(self, chico_home, config_file, monkeypatch):
        result = runner.invoke(app, ["sync", "nonexistent"])
        assert "not found" in result.output


# ── no changes ────────────────────────────────────────────────────────────────


class TestSyncNoChanges:
    def test_exits_cleanly_when_nothing_to_sync(
        self, chico_home, config_file, monkeypatch
    ):
        monkeypatch.setattr("chico.cli.sync.execute_apply", lambda _: _empty_result())
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0

    def test_shows_up_to_date_message(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr("chico.cli.sync.execute_apply", lambda _: _empty_result())
        result = runner.invoke(app, ["sync"])
        assert "Nothing to sync" in result.output


# ── successful sync ───────────────────────────────────────────────────────────


class TestSyncSuccess:
    def test_exits_cleanly_with_changes(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply", lambda _: _result_with_changes(ok=2)
        )
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0

    def test_shows_synced_count(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply", lambda _: _result_with_changes(ok=2)
        )
        result = runner.invoke(app, ["sync"])
        assert "2" in result.output

    def test_shows_ok_status(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply", lambda _: _result_with_changes(ok=1)
        )
        result = runner.invoke(app, ["sync"])
        assert "ok" in result.output

    def test_shows_resource_id(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply", lambda _: _result_with_changes(ok=1)
        )
        result = runner.invoke(app, ["sync"])
        assert "/file-ok-0.md" in result.output

    def test_shows_add_symbol(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply", lambda _: _result_with_changes(ok=1)
        )
        result = runner.invoke(app, ["sync"])
        assert "+" in result.output


# ── sync with errors ──────────────────────────────────────────────────────────


class TestSyncWithErrors:
    def test_exits_with_error_code(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply",
            lambda _: _result_with_changes(ok=1, errors=1),
        )
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 1

    def test_shows_error_status(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply",
            lambda _: _result_with_changes(ok=0, errors=1),
        )
        result = runner.invoke(app, ["sync"])
        assert "error" in result.output

    def test_shows_error_message(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply",
            lambda _: _result_with_changes(ok=0, errors=1),
        )
        result = runner.invoke(app, ["sync"])
        assert "Permission denied" in result.output

    def test_shows_summary_with_error_count(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.sync.execute_apply",
            lambda _: _result_with_changes(ok=1, errors=1),
        )
        result = runner.invoke(app, ["sync"])
        assert "1 error" in result.output


# ── exception handling ────────────────────────────────────────────────────────


class TestSyncException:
    def test_exits_with_error_on_fetch_failure(
        self, chico_home, config_file, monkeypatch
    ):
        def _raise(_config):
            raise SourceFetchError("Network error")

        monkeypatch.setattr("chico.cli.sync.execute_apply", _raise)
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 1

    def test_shows_error_message_on_fetch_failure(
        self, chico_home, config_file, monkeypatch
    ):
        def _raise(_config):
            raise SourceFetchError("Network error")

        monkeypatch.setattr("chico.cli.sync.execute_apply", _raise)
        result = runner.invoke(app, ["sync"])
        assert "Network error" in result.output
