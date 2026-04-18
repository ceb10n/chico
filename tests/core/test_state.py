"""Tests for chico.core.state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chico.core.state import State, load_state, save_state


@pytest.fixture()
def state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "state.json"
    monkeypatch.setattr("chico.core.state.STATE_FILE", path)
    return path


class TestState:
    def test_defaults(self):
        state = State()
        assert state.status == "idle"
        assert state.last_run is None
        assert state.resources == []
        assert state.versions == {}

    def test_versions_are_independent_between_instances(self):
        s1 = State()
        s2 = State()
        s1.versions["source-a"] = "abc"
        assert "source-a" not in s2.versions

    def test_resources_are_independent_between_instances(self):
        s1 = State()
        s2 = State()
        s1.resources.append({"id": "r1"})
        assert s2.resources == []

    def test_record_version(self):
        state = State()
        state.record_version("kiro-configs", "abc123def456")
        assert state.versions["kiro-configs"] == "abc123def456"

    def test_record_version_overwrites_previous(self):
        state = State()
        state.record_version("kiro-configs", "aaa")
        state.record_version("kiro-configs", "bbb")
        assert state.versions["kiro-configs"] == "bbb"

    def test_get_version_returns_hash(self):
        state = State()
        state.record_version("kiro-configs", "abc123")
        assert state.get_version("kiro-configs") == "abc123"

    def test_get_version_returns_none_when_not_tracked(self):
        state = State()
        assert state.get_version("unknown-source") is None


class TestLoadState:
    def test_loads_existing_state(self, state_file: Path):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": None,
                    "resources": [],
                    "versions": {"kiro-configs": "abc123"},
                }
            )
        )
        state = load_state()
        assert state.versions["kiro-configs"] == "abc123"

    def test_returns_default_state_when_file_missing(self, state_file: Path):
        state = load_state()
        assert state.status == "idle"
        assert state.versions == {}

    def test_loads_all_fields(self, state_file: Path):
        state_file.write_text(
            json.dumps(
                {
                    "status": "idle",
                    "last_run": {"result": "success", "changes": 3},
                    "resources": [{"id": "r1"}],
                    "versions": {"src": "deadbeef"},
                }
            )
        )
        state = load_state()
        assert state.last_run == {"result": "success", "changes": 3}
        assert state.resources == [{"id": "r1"}]
        assert state.versions == {"src": "deadbeef"}


class TestSaveState:
    def test_writes_state_to_file(self, state_file: Path):
        state = State()
        state.record_version("kiro-configs", "abc123")
        save_state(state)
        raw = json.loads(state_file.read_text())
        assert raw["versions"]["kiro-configs"] == "abc123"

    def test_roundtrip(self, state_file: Path):
        state = State()
        state.record_version("src-a", "aaa")
        state.record_version("src-b", "bbb")
        save_state(state)
        loaded = load_state()
        assert loaded.versions == {"src-a": "aaa", "src-b": "bbb"}

    def test_creates_parent_dir_if_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        deep = tmp_path / "a" / "b" / "state.json"
        monkeypatch.setattr("chico.core.state.STATE_FILE", deep)
        save_state(State())
        assert deep.exists()

    def test_written_file_is_valid_json(self, state_file: Path):
        save_state(State())
        json.loads(state_file.read_text())  # must not raise
