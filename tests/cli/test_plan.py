"""Tests for chico.cli.plan (chico plan command)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chico.cli.main import app
from chico.core.log import _LOGGER_NAME
from chico.core.plan import Plan, RiskLevel
from chico.core.resource import ChangeType, Diff
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


# ── no config ─────────────────────────────────────────────────────────────────


class TestPlanNoConfig:
    def test_exits_with_error_when_no_config(self, chico_home, tmp_path, monkeypatch):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["plan"])
        assert result.exit_code == 1

    def test_shows_error_message_when_no_config(
        self, chico_home, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["plan"])
        assert "Config file not found" in result.output

    def test_exits_with_error_for_unknown_source(
        self, chico_home, config_file, monkeypatch
    ):
        result = runner.invoke(app, ["plan", "nonexistent"])
        assert result.exit_code == 1

    def test_shows_error_for_unknown_source(
        self, chico_home, config_file, monkeypatch
    ):
        result = runner.invoke(app, ["plan", "nonexistent"])
        assert "not found" in result.output


# ── no changes ────────────────────────────────────────────────────────────────


class TestPlanNoChanges:
    def test_exits_cleanly_when_no_changes(self, chico_home, config_file, monkeypatch):
        empty_plan = Plan(plan_id="test-id", changes=[], risk_level=RiskLevel.NONE)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: empty_plan)
        result = runner.invoke(app, ["plan"])
        assert result.exit_code == 0

    def test_shows_no_changes_message(self, chico_home, config_file, monkeypatch):
        empty_plan = Plan(plan_id="test-id", changes=[], risk_level=RiskLevel.NONE)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: empty_plan)
        result = runner.invoke(app, ["plan"])
        assert "No changes" in result.output


# ── with changes ──────────────────────────────────────────────────────────────


class TestPlanWithChanges:
    def test_exits_cleanly_with_changes(self, chico_home, config_file, monkeypatch):
        diff = Diff(
            change_type=ChangeType.ADD,
            resource_id="/home/user/.kiro/steering/product.md",
        )
        test_plan = Plan(plan_id="plan-abc", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: test_plan)
        result = runner.invoke(app, ["plan"])
        assert result.exit_code == 0

    def test_shows_change_count(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/file.md")
        test_plan = Plan(plan_id="plan-abc", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: test_plan)
        result = runner.invoke(app, ["plan"])
        assert "1" in result.output

    def test_shows_risk_level(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/file.md")
        test_plan = Plan(plan_id="plan-abc", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: test_plan)
        result = runner.invoke(app, ["plan"])
        assert "low" in result.output

    def test_shows_plan_id(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/file.md")
        test_plan = Plan(plan_id="plan-abc", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: test_plan)
        result = runner.invoke(app, ["plan"])
        assert "plan-abc" in result.output

    def test_shows_add_symbol(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/file.md")
        test_plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: test_plan)
        result = runner.invoke(app, ["plan"])
        assert "+" in result.output

    def test_shows_modify_symbol(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.MODIFY, resource_id="/some/file.md")
        test_plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.MEDIUM)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: test_plan)
        result = runner.invoke(app, ["plan"])
        assert "~" in result.output

    def test_shows_remove_symbol(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.REMOVE, resource_id="/some/file.md")
        test_plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.HIGH)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: test_plan)
        result = runner.invoke(app, ["plan"])
        assert "-" in result.output

    def test_shows_resource_id(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/specific/file.md")
        test_plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.plan.compute_plan", lambda _: test_plan)
        result = runner.invoke(app, ["plan"])
        assert "/some/specific/file.md" in result.output


# ── fetch error ───────────────────────────────────────────────────────────────


class TestPlanFetchError:
    def test_exits_with_error_on_fetch_failure(
        self, chico_home, config_file, monkeypatch
    ):
        def _raise(_config):
            raise SourceFetchError("Network error")

        monkeypatch.setattr("chico.cli.plan.compute_plan", _raise)
        result = runner.invoke(app, ["plan"])
        assert result.exit_code == 1

    def test_shows_error_message_on_fetch_failure(
        self, chico_home, config_file, monkeypatch
    ):
        def _raise(_config):
            raise SourceFetchError("Network error")

        monkeypatch.setattr("chico.cli.plan.compute_plan", _raise)
        result = runner.invoke(app, ["plan"])
        assert "Network error" in result.output
