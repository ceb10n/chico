"""Tests for chico.cli.init and chico.cli.main (chico init command)."""

from __future__ import annotations

import json
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
    """Remove all handlers from the chico logger between tests."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture()
def chico_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all chico paths to a temp directory."""
    monkeypatch.setattr("chico.cli.init.CHICO_DIR", tmp_path)
    monkeypatch.setattr("chico.cli.init.CONFIG_FILE", tmp_path / "config.yaml")
    monkeypatch.setattr("chico.cli.init.STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr("chico.core.log.CHICO_DIR", tmp_path)
    monkeypatch.setattr("chico.core.log.LOG_FILE", tmp_path / "chico.log")
    return tmp_path


class TestInitCommand:
    def test_creates_chico_dir(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert chico_home.exists()

    def test_creates_config_file(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(app, ["init"])
        assert (chico_home / "config.yaml").exists()

    def test_creates_state_file(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(app, ["init"])
        assert (chico_home / "state.json").exists()

    def test_config_file_has_correct_structure(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(app, ["init"])
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["providers"] == []
        assert config["sources"] == []
        assert config["policy"]["strategy"] == "safe"

    def test_state_file_has_correct_structure(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(app, ["init"])
        state = json.loads((chico_home / "state.json").read_text())
        assert state["status"] == "idle"
        assert state["last_run"] is None
        assert state["resources"] == []
        assert state["versions"] == {}

    def test_output_confirms_initialization(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(app, ["init"])
        assert "Initialized chico" in result.output

    def test_output_shows_next_steps(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(app, ["init"])
        assert "Next steps" in result.output
        assert "chico plan" in result.output
        assert "chico apply" in result.output

    def test_already_initialized_exits_cleanly(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "Already initialized" in result.output

    def test_already_initialized_does_not_overwrite_config(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(app, ["init"])
        config_file = chico_home / "config.yaml"
        config_file.write_text("modified: true\n")
        runner.invoke(app, ["init"])
        assert config_file.read_text() == "modified: true\n"

    def test_is_idempotent(self, chico_home: Path):
        chico_home.rmdir()
        r1 = runner.invoke(app, ["init"])
        r2 = runner.invoke(app, ["init"])
        assert r1.exit_code == 0
        assert r2.exit_code == 0


# ── init with source flags ────────────────────────────────────────────────────


class TestInitWithSource:
    def test_exits_cleanly_with_source_flags(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "steering/"],
        )
        assert result.exit_code == 0

    def test_writes_provider_to_config(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "steering/"],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["providers"][0]["type"] == "kiro"

    def test_writes_source_to_config(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "steering/"],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["sources"][0]["repo"] == "org/repo"
        assert config["sources"][0]["path"] == "steering/"

    def test_source_name_derived_from_repo(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/my-configs", "--path", "p/"],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["sources"][0]["name"] == "my-configs"

    def test_uses_default_branch(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "p/"],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["sources"][0]["branch"] == "main"

    def test_uses_default_level(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "p/"],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["providers"][0]["level"] == "global"

    def test_uses_default_target(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "p/"],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["sources"][0]["target"] == "kiro"

    def test_respects_custom_branch(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            [
                "init",
                "--source",
                "github",
                "--repo",
                "org/repo",
                "--path",
                "p/",
                "--branch",
                "develop",
            ],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["sources"][0]["branch"] == "develop"

    def test_respects_custom_level(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            [
                "init",
                "--source",
                "github",
                "--repo",
                "org/repo",
                "--path",
                "p/",
                "--level",
                "project",
            ],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["providers"][0]["level"] == "project"

    def test_project_level_records_cwd_kiro_as_path(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            [
                "init",
                "--source",
                "github",
                "--repo",
                "org/repo",
                "--path",
                "p/",
                "--level",
                "project",
            ],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        expected = str(Path.cwd() / ".kiro")
        assert config["providers"][0]["path"] == expected

    def test_global_level_does_not_record_path(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            [
                "init",
                "--source",
                "github",
                "--repo",
                "org/repo",
                "--path",
                "p/",
                "--level",
                "global",
            ],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert "path" not in config["providers"][0]

    def test_respects_custom_target(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            [
                "init",
                "--source",
                "github",
                "--repo",
                "org/repo",
                "--path",
                "p/",
                "--target",
                "kiro-global",
            ],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["sources"][0]["target"] == "kiro-global"
        assert config["providers"][0]["name"] == "kiro-global"

    def test_defaults_source_prefix_to_path(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "steering/"],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["sources"][0]["source_prefix"] == "steering/"

    def test_respects_custom_source_prefix(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(
            app,
            [
                "init",
                "--source",
                "github",
                "--repo",
                "org/repo",
                "--path",
                "steering/",
                "--source-prefix",
                "steering/subdir/",
            ],
        )
        config = yaml.safe_load((chico_home / "config.yaml").read_text())
        assert config["sources"][0]["source_prefix"] == "steering/subdir/"

    def test_fails_without_repo(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(app, ["init", "--source", "github", "--path", "p/"])
        assert result.exit_code == 1

    def test_shows_error_without_repo(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(app, ["init", "--source", "github", "--path", "p/"])
        assert "--repo" in result.output

    def test_fails_without_path(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(
            app, ["init", "--source", "github", "--repo", "org/repo"]
        )
        assert result.exit_code == 1

    def test_shows_error_without_path(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(
            app, ["init", "--source", "github", "--repo", "org/repo"]
        )
        assert "--path" in result.output

    def test_fails_for_unsupported_source_type(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(
            app, ["init", "--source", "s3", "--repo", "org/repo", "--path", "p/"]
        )
        assert result.exit_code == 1

    def test_shows_error_for_unsupported_source_type(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(
            app, ["init", "--source", "s3", "--repo", "org/repo", "--path", "p/"]
        )
        assert "s3" in result.output

    def test_shows_repo_in_output(self, chico_home: Path):
        chico_home.rmdir()
        result = runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "steering/"],
        )
        assert "org/repo" in result.output

    def test_already_initialized_with_flags_exits_cleanly(self, chico_home: Path):
        chico_home.rmdir()
        runner.invoke(app, ["init"])
        result = runner.invoke(
            app,
            ["init", "--source", "github", "--repo", "org/repo", "--path", "p/"],
        )
        assert result.exit_code == 0
        assert "Already initialized" in result.output


class TestMainApp:
    def test_help_exits_cleanly(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_lists_init_command(self):
        result = runner.invoke(app, ["--help"])
        assert "init" in result.output

    def test_init_help_exits_cleanly(self):
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert "Usage" in result.output
