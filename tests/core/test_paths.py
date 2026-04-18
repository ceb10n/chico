"""Tests for chico.core.paths."""

from __future__ import annotations

from pathlib import Path

from chico.core.paths import CHICO_DIR, CONFIG_FILE, LOG_FILE, STATE_FILE


class TestPaths:
    def test_chico_dir_is_under_home(self):
        assert Path.home() / ".chico" == CHICO_DIR

    def test_config_file_is_under_chico_dir(self):
        assert CONFIG_FILE == CHICO_DIR / "config.yaml"

    def test_state_file_is_under_chico_dir(self):
        assert STATE_FILE == CHICO_DIR / "state.json"

    def test_log_file_is_under_chico_dir(self):
        assert LOG_FILE == CHICO_DIR / "chico.log"

    def test_all_paths_are_path_instances(self):
        for p in (CHICO_DIR, CONFIG_FILE, STATE_FILE, LOG_FILE):
            assert isinstance(p, Path)

    def test_config_file_name(self):
        assert CONFIG_FILE.name == "config.yaml"

    def test_state_file_name(self):
        assert STATE_FILE.name == "state.json"

    def test_log_file_name(self):
        assert LOG_FILE.name == "chico.log"
