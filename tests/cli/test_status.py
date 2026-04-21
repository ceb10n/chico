"""Tests for chico.cli.status (chico status command)."""

from __future__ import annotations

import json
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
def state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    sf = tmp_path / "state.json"
    monkeypatch.setattr("chico.core.state.STATE_FILE", sf)
    return sf


# ── no state file ──────────────────────────────────────────────────────────────


class TestStatusNoState:
    def test_exits_cleanly_when_no_state(self, chico_home, state_file):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0

    def test_shows_idle_status(self, chico_home, state_file):
        result = runner.invoke(app, ["status"])
        assert "idle" in result.output

    def test_shows_no_runs_message(self, chico_home, state_file):
        result = runner.invoke(app, ["status"])
        assert "No previous runs" in result.output

    def test_shows_no_sources_when_empty(self, chico_home, state_file):
        result = runner.invoke(app, ["status"])
        assert "no sources" in result.output.lower() or "Sources" in result.output


# ── with last run ─────────────────────────────────────────────────────────────


class TestStatusWithLastRun:
    def test_shows_last_run_timestamp(self, chico_home, state_file):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": {
                        "timestamp": "2026-04-19T10:00:00+00:00",
                        "applied": 3,
                        "errors": 0,
                    },
                    "resources": [],
                    "versions": {},
                }
            )
        )
        result = runner.invoke(app, ["status"])
        assert "2026-04-19" in result.output

    def test_shows_applied_count(self, chico_home, state_file):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": {
                        "timestamp": "2026-04-19T10:00:00+00:00",
                        "applied": 3,
                        "errors": 0,
                    },
                    "resources": [],
                    "versions": {},
                }
            )
        )
        result = runner.invoke(app, ["status"])
        assert "3" in result.output

    def test_shows_error_count(self, chico_home, state_file):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": {
                        "timestamp": "2026-04-19T10:00:00+00:00",
                        "applied": 2,
                        "errors": 1,
                    },
                    "resources": [],
                    "versions": {},
                }
            )
        )
        result = runner.invoke(app, ["status"])
        assert "1" in result.output


# ── with source versions ───────────────────────────────────────────────────────


class TestStatusWithVersions:
    def test_shows_source_name(self, chico_home, state_file):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": None,
                    "resources": [],
                    "versions": {"my-source": "abc123"},
                }
            )
        )
        result = runner.invoke(app, ["status"])
        assert "my-source" in result.output

    def test_shows_source_version(self, chico_home, state_file):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": None,
                    "resources": [],
                    "versions": {"my-source": "abc123def456"},
                }
            )
        )
        result = runner.invoke(app, ["status"])
        assert "abc123def456" in result.output

    def test_shows_multiple_sources(self, chico_home, state_file):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": None,
                    "resources": [],
                    "versions": {"source-a": "aaa", "source-b": "bbb"},
                }
            )
        )
        result = runner.invoke(app, ["status"])
        assert "source-a" in result.output
        assert "source-b" in result.output


# ── with resources ─────────────────────────────────────────────────────────────


class TestStatusWithResources:
    def test_shows_resource_count(self, chico_home, state_file):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": None,
                    "resources": [
                        {"resource_id": "/file-a.md", "status": "ok"},
                        {"resource_id": "/file-b.md", "status": "ok"},
                    ],
                    "versions": {},
                }
            )
        )
        result = runner.invoke(app, ["status"])
        assert "2" in result.output
