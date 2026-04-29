"""Tests for chico.cli.apply (chico apply command)."""

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


def _empty_apply_result() -> ApplyResult:
    return ApplyResult(
        plan=Plan(plan_id="test-id", changes=[], risk_level=RiskLevel.NONE),
        results=[],
    )


def _apply_result_with_changes(ok: int = 1, errors: int = 0) -> ApplyResult:
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
    risk = RiskLevel.LOW if not errors else RiskLevel.LOW
    return ApplyResult(
        plan=Plan(plan_id="plan-abc", changes=changes, risk_level=risk),
        results=results,
    )


# ── no config ─────────────────────────────────────────────────────────────────


class TestApplyNoConfig:
    def test_exits_with_error_when_no_config(self, chico_home, tmp_path, monkeypatch):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["apply"])
        assert result.exit_code == 1

    def test_shows_error_message_when_no_config(
        self, chico_home, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["apply"])
        assert "Config file not found" in result.output

    def test_exits_with_error_for_unknown_source(
        self, chico_home, config_file, monkeypatch
    ):
        result = runner.invoke(app, ["apply", "nonexistent"])
        assert result.exit_code == 1

    def test_shows_error_for_unknown_source(self, chico_home, config_file, monkeypatch):
        result = runner.invoke(app, ["apply", "nonexistent"])
        assert "not found" in result.output


# ── no changes ────────────────────────────────────────────────────────────────


class TestApplyNoChanges:
    def test_exits_cleanly_when_no_changes(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply", lambda _: _empty_apply_result()
        )
        result = runner.invoke(app, ["apply"])
        assert result.exit_code == 0

    def test_shows_no_changes_message(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply", lambda _: _empty_apply_result()
        )
        result = runner.invoke(app, ["apply"])
        assert "No changes" in result.output


# ── successful apply ──────────────────────────────────────────────────────────


class TestApplySuccess:
    def test_exits_cleanly_with_applied_changes(
        self, chico_home, config_file, monkeypatch
    ):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply", lambda _: _apply_result_with_changes(ok=2)
        )
        result = runner.invoke(app, ["apply"])
        assert result.exit_code == 0

    def test_shows_applied_count(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply", lambda _: _apply_result_with_changes(ok=2)
        )
        result = runner.invoke(app, ["apply"])
        assert "2" in result.output

    def test_shows_ok_status(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply", lambda _: _apply_result_with_changes(ok=1)
        )
        result = runner.invoke(app, ["apply"])
        assert "ok" in result.output

    def test_shows_resource_id(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply", lambda _: _apply_result_with_changes(ok=1)
        )
        result = runner.invoke(app, ["apply"])
        assert "/file-ok-0.md" in result.output

    def test_shows_add_symbol(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply", lambda _: _apply_result_with_changes(ok=1)
        )
        result = runner.invoke(app, ["apply"])
        assert "+" in result.output


# ── apply with errors ─────────────────────────────────────────────────────────


class TestApplyWithErrors:
    def test_exits_with_error_code_when_apply_fails(
        self, chico_home, config_file, monkeypatch
    ):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply",
            lambda _: _apply_result_with_changes(ok=1, errors=1),
        )
        result = runner.invoke(app, ["apply"])
        assert result.exit_code == 1

    def test_shows_error_status(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply",
            lambda _: _apply_result_with_changes(ok=0, errors=1),
        )
        result = runner.invoke(app, ["apply"])
        assert "error" in result.output

    def test_shows_error_message(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply",
            lambda _: _apply_result_with_changes(ok=0, errors=1),
        )
        result = runner.invoke(app, ["apply"])
        assert "Permission denied" in result.output

    def test_shows_summary_with_error_count(self, chico_home, config_file, monkeypatch):
        monkeypatch.setattr(
            "chico.cli.apply.execute_apply",
            lambda _: _apply_result_with_changes(ok=1, errors=1),
        )
        result = runner.invoke(app, ["apply"])
        assert "1 error" in result.output


# ── fetch/apply exception ─────────────────────────────────────────────────────


class TestApplyException:
    def test_exits_with_error_on_fetch_failure(
        self, chico_home, config_file, monkeypatch
    ):
        def _raise(_config):
            raise SourceFetchError("Network error")

        monkeypatch.setattr("chico.cli.apply.execute_apply", _raise)
        result = runner.invoke(app, ["apply"])
        assert result.exit_code == 1

    def test_shows_error_message_on_fetch_failure(
        self, chico_home, config_file, monkeypatch
    ):
        def _raise(_config):
            raise SourceFetchError("Network error")

        monkeypatch.setattr("chico.cli.apply.execute_apply", _raise)
        result = runner.invoke(app, ["apply"])
        assert "Network error" in result.output
