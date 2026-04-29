"""Tests for chico.cli.add (chico add source / chico add provider)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml
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
    monkeypatch.setattr("chico.cli.add.CONFIG_FILE", tmp_path / "config.yaml")
    return tmp_path


@pytest.fixture()
def config_file(chico_home: Path) -> Path:
    cfg = chico_home / "config.yaml"
    cfg.write_text(
        yaml.dump(
            {
                "providers": [{"name": "kiro", "type": "kiro", "level": "global"}],
                "sources": [
                    {
                        "name": "first",
                        "type": "github",
                        "repo": "org/first",
                        "path": "p/",
                        "source_prefix": "p/",
                        "branch": "main",
                        "target": "kiro",
                    }
                ],
                "policy": {"strategy": "safe"},
            }
        )
    )
    return cfg


# ── add source ────────────────────────────────────────────────────────────────


class TestAddSource:
    def test_exits_cleanly(self, config_file):
        result = runner.invoke(
            app, ["add", "source", "--repo", "org/second", "--path", "q/"]
        )
        assert result.exit_code == 0

    def test_appends_source(self, config_file):
        runner.invoke(
            app, ["add", "source", "--repo", "org/second", "--path", "q/"]
        )
        config = yaml.safe_load(config_file.read_text())
        assert len(config["sources"]) == 2
        assert config["sources"][1]["name"] == "second"

    def test_preserves_existing_source(self, config_file):
        runner.invoke(
            app, ["add", "source", "--repo", "org/second", "--path", "q/"]
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["sources"][0]["name"] == "first"

    def test_shows_confirmation(self, config_file):
        result = runner.invoke(
            app, ["add", "source", "--repo", "org/second", "--path", "q/"]
        )
        assert "Added source" in result.output
        assert "second" in result.output

    def test_uses_repo_name_as_default_name(self, config_file):
        runner.invoke(
            app, ["add", "source", "--repo", "org/my-configs", "--path", "q/"]
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["sources"][1]["name"] == "my-configs"

    def test_respects_custom_name(self, config_file):
        runner.invoke(
            app,
            [
                "add", "source",
                "--repo", "org/second", "--path", "q/", "--name", "custom-name",
            ],
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["sources"][1]["name"] == "custom-name"

    def test_respects_custom_branch(self, config_file):
        runner.invoke(
            app,
            [
                "add", "source",
                "--repo", "org/second", "--path", "q/", "--branch", "develop",
            ],
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["sources"][1]["branch"] == "develop"

    def test_respects_custom_target(self, config_file):
        runner.invoke(
            app,
            [
                "add", "source",
                "--repo", "org/second", "--path", "q/", "--target", "kiro-local",
            ],
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["sources"][1]["target"] == "kiro-local"

    def test_respects_custom_source_prefix(self, config_file):
        runner.invoke(
            app,
            [
                "add", "source",
                "--repo", "org/second", "--path", "q/",
                "--source-prefix", "custom/",
            ],
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["sources"][1]["source_prefix"] == "custom/"

    def test_defaults_source_prefix_to_path(self, config_file):
        runner.invoke(
            app, ["add", "source", "--repo", "org/second", "--path", "steering/"]
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["sources"][1]["source_prefix"] == "steering/"

    def test_fails_for_duplicate_name(self, config_file):
        result = runner.invoke(
            app, ["add", "source", "--repo", "org/first", "--path", "q/"]
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_fails_for_unsupported_type(self, config_file):
        result = runner.invoke(
            app,
            [
                "add", "source",
                "--repo", "org/second", "--path", "q/", "--type", "s3",
            ],
        )
        assert result.exit_code == 1
        assert "s3" in result.output

    def test_fails_when_no_config(self, chico_home):
        result = runner.invoke(
            app, ["add", "source", "--repo", "org/repo", "--path", "p/"]
        )
        assert result.exit_code == 1
        assert "no config file" in result.output.lower()


# ── add provider ──────────────────────────────────────────────────────────────


class TestAddProvider:
    def test_exits_cleanly(self, config_file):
        result = runner.invoke(
            app, ["add", "provider", "--name", "kiro-local"]
        )
        assert result.exit_code == 0

    def test_appends_provider(self, config_file):
        runner.invoke(app, ["add", "provider", "--name", "kiro-local"])
        config = yaml.safe_load(config_file.read_text())
        assert len(config["providers"]) == 2
        assert config["providers"][1]["name"] == "kiro-local"

    def test_preserves_existing_provider(self, config_file):
        runner.invoke(app, ["add", "provider", "--name", "kiro-local"])
        config = yaml.safe_load(config_file.read_text())
        assert config["providers"][0]["name"] == "kiro"

    def test_shows_confirmation(self, config_file):
        result = runner.invoke(
            app, ["add", "provider", "--name", "kiro-local"]
        )
        assert "Added provider" in result.output
        assert "kiro-local" in result.output

    def test_defaults_to_global_level(self, config_file):
        runner.invoke(app, ["add", "provider", "--name", "kiro-new"])
        config = yaml.safe_load(config_file.read_text())
        assert config["providers"][1]["level"] == "global"

    def test_global_has_no_path(self, config_file):
        runner.invoke(app, ["add", "provider", "--name", "kiro-new"])
        config = yaml.safe_load(config_file.read_text())
        assert "path" not in config["providers"][1]

    def test_project_level_defaults_path_to_cwd(self, config_file):
        runner.invoke(
            app,
            ["add", "provider", "--name", "kiro-local", "--level", "project"],
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["providers"][1]["path"] == str(Path.cwd() / ".kiro")

    def test_project_level_respects_custom_path(self, config_file, tmp_path):
        custom = str(tmp_path / "my-project" / ".kiro")
        runner.invoke(
            app,
            [
                "add", "provider",
                "--name", "kiro-local", "--level", "project", "--path", custom,
            ],
        )
        config = yaml.safe_load(config_file.read_text())
        assert config["providers"][1]["path"] == custom

    def test_fails_for_duplicate_name(self, config_file):
        result = runner.invoke(
            app, ["add", "provider", "--name", "kiro"]
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_fails_for_unsupported_type(self, config_file):
        result = runner.invoke(
            app,
            ["add", "provider", "--name", "new", "--type", "unknown"],
        )
        assert result.exit_code == 1
        assert "unknown" in result.output

    def test_fails_when_no_config(self, chico_home):
        result = runner.invoke(
            app, ["add", "provider", "--name", "kiro-local"]
        )
        assert result.exit_code == 1
        assert "no config file" in result.output.lower()
