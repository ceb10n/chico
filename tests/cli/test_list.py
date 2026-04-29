"""Tests for chico.cli.list (chico list command)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chico.cli.main import app
from chico.core.log import _LOGGER_NAME

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


class TestListNoConfig:
    def test_exits_with_error_when_no_config(self, chico_home, tmp_path, monkeypatch):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 1

    def test_shows_error_message_when_no_config(
        self, chico_home, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "missing.yaml")
        result = runner.invoke(app, ["list"])
        assert "Config file not found" in result.output


# ── empty config ──────────────────────────────────────────────────────────────


class TestListEmpty:
    def test_exits_cleanly_when_empty(self, chico_home, config_file):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_shows_no_config_message(self, chico_home, config_file):
        result = runner.invoke(app, ["list"])
        assert "No providers or sources configured" in result.output


# ── with providers and sources ────────────────────────────────────────────────


_FULL_CONFIG = """\
providers:
  - name: kiro
    type: kiro
    level: global
  - name: kiro-local
    type: kiro
    level: project
    path: /home/user/my-project/.kiro
sources:
  - name: steering
    type: github
    repo: org/config
    path: steering
    branch: main
    target: kiro
    source_prefix: steering/
  - name: hooks
    type: github
    repo: org/hooks
    path: hooks
    branch: develop
    target: kiro
policy:
  strategy: safe
"""


@pytest.fixture()
def full_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(_FULL_CONFIG)
    monkeypatch.setattr("chico.core.config.CONFIG_FILE", cfg)
    return cfg


class TestListWithConfig:
    def test_exits_cleanly(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    def test_shows_provider_count(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "Providers (2)" in result.output

    def test_shows_source_count(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "Sources (2)" in result.output

    def test_shows_provider_name(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "kiro" in result.output

    def test_shows_provider_level(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "global" in result.output

    def test_shows_project_provider_path(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "/home/user/my-project/.kiro" in result.output

    def test_shows_source_name(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "steering" in result.output
        assert "hooks" in result.output

    def test_shows_source_repo(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "org/config" in result.output
        assert "org/hooks" in result.output

    def test_shows_source_branch(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "develop" in result.output

    def test_shows_source_target(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "target: kiro" in result.output

    def test_shows_source_prefix(self, chico_home, full_config):
        result = runner.invoke(app, ["list"])
        assert "prefix: steering/" in result.output


# ── providers only ────────────────────────────────────────────────────────────


class TestListProvidersOnly:
    def test_shows_providers_without_sources(self, chico_home, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "providers:\n  - name: kiro\n    type: kiro\n    level: global\n"
            "sources: []\npolicy:\n  strategy: safe\n"
        )
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", cfg)
        result = runner.invoke(app, ["list"])
        assert "Providers (1)" in result.output
        assert "Sources" not in result.output


# ── sources only ──────────────────────────────────────────────────────────────


class TestListSourcesOnly:
    def test_shows_sources_without_providers(self, chico_home, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "providers: []\nsources:\n  - name: s\n    type: github\n"
            "    repo: o/r\n    path: p\n    branch: main\n    target: kiro\n"
            "policy:\n  strategy: safe\n"
        )
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", cfg)
        result = runner.invoke(app, ["list"])
        assert "Providers" not in result.output
        assert "Sources (1)" in result.output

    def test_shows_none_for_empty_target(self, chico_home, tmp_path, monkeypatch):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "providers: []\nsources:\n  - name: s\n    type: github\n"
            "    repo: o/r\n    path: p\n    branch: main\n"
            "policy:\n  strategy: safe\n"
        )
        monkeypatch.setattr("chico.core.config.CONFIG_FILE", cfg)
        result = runner.invoke(app, ["list"])
        assert "(none)" in result.output
