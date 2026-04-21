"""Tests for chico.cli.diff (chico diff command)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chico.cli.main import app
from chico.core.log import _LOGGER_NAME
from chico.core.plan import Plan, RiskLevel
from chico.core.resource import ChangeType, Diff, FieldChange
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


class TestDiffNoConfig:
    def test_exits_with_error_when_no_config(self, chico_home, tmp_path, monkeypatch):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["diff"])
        assert result.exit_code == 1

    def test_shows_error_message_when_no_config(
        self, chico_home, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["diff"])
        assert "Config file not found" in result.output


# ── no changes ────────────────────────────────────────────────────────────────


class TestDiffNoChanges:
    def test_exits_cleanly_when_no_changes(self, chico_home, config_file, monkeypatch):
        empty_plan = Plan(plan_id="test-id", changes=[], risk_level=RiskLevel.NONE)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: empty_plan)
        result = runner.invoke(app, ["diff"])
        assert result.exit_code == 0

    def test_shows_no_changes_message(self, chico_home, config_file, monkeypatch):
        empty_plan = Plan(plan_id="test-id", changes=[], risk_level=RiskLevel.NONE)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: empty_plan)
        result = runner.invoke(app, ["diff"])
        assert "No changes" in result.output


# ── with changes ──────────────────────────────────────────────────────────────


class TestDiffWithChanges:
    def test_exits_cleanly_with_add(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/file.md")
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert result.exit_code == 0

    def test_shows_change_count(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/file.md")
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "1" in result.output

    def test_shows_add_symbol(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/file.md")
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "+" in result.output

    def test_shows_modify_symbol(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.MODIFY, resource_id="/some/file.md")
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.MEDIUM)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "~" in result.output

    def test_shows_remove_symbol(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.REMOVE, resource_id="/some/file.md")
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.HIGH)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "-" in result.output

    def test_shows_resource_id(self, chico_home, config_file, monkeypatch):
        diff = Diff(change_type=ChangeType.ADD, resource_id="/some/specific/file.md")
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.LOW)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "/some/specific/file.md" in result.output


# ── modify with field changes ─────────────────────────────────────────────────


class TestDiffWithModify:
    def test_shows_field_name_for_modify(self, chico_home, config_file, monkeypatch):
        diff = Diff(
            change_type=ChangeType.MODIFY,
            resource_id="/some/file.md",
            changes={"content": FieldChange(from_value="old", to_value="new")},
        )
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.MEDIUM)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "content" in result.output

    def test_shows_from_value_for_modify(self, chico_home, config_file, monkeypatch):
        diff = Diff(
            change_type=ChangeType.MODIFY,
            resource_id="/some/file.md",
            changes={
                "content": FieldChange(from_value="old text", to_value="new text")
            },
        )
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.MEDIUM)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "old text" in result.output

    def test_shows_to_value_for_modify(self, chico_home, config_file, monkeypatch):
        diff = Diff(
            change_type=ChangeType.MODIFY,
            resource_id="/some/file.md",
            changes={
                "content": FieldChange(from_value="old text", to_value="new text")
            },
        )
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.MEDIUM)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "new text" in result.output

    def test_truncates_long_values(self, chico_home, config_file, monkeypatch):
        long_from = "A" * 100
        long_to = "B" * 100
        diff = Diff(
            change_type=ChangeType.MODIFY,
            resource_id="/some/file.md",
            changes={"content": FieldChange(from_value=long_from, to_value=long_to)},
        )
        plan = Plan(plan_id="p", changes=[diff], risk_level=RiskLevel.MEDIUM)
        monkeypatch.setattr("chico.cli.diff.compute_plan", lambda _: plan)
        result = runner.invoke(app, ["diff"])
        assert "..." in result.output


# ── fetch error ───────────────────────────────────────────────────────────────


class TestDiffFetchError:
    def test_exits_with_error_on_fetch_failure(
        self, chico_home, config_file, monkeypatch
    ):
        def _raise(_config):
            raise SourceFetchError("Network error")

        monkeypatch.setattr("chico.cli.diff.compute_plan", _raise)
        result = runner.invoke(app, ["diff"])
        assert result.exit_code == 1

    def test_shows_error_message_on_fetch_failure(
        self, chico_home, config_file, monkeypatch
    ):
        def _raise(_config):
            raise SourceFetchError("Network error")

        monkeypatch.setattr("chico.cli.diff.compute_plan", _raise)
        result = runner.invoke(app, ["diff"])
        assert "Network error" in result.output
