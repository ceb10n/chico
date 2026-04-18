"""Tests for chico.core.log."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from chico.core.log import _LOGGER_NAME, _JsonFormatter, setup_logging


@pytest.fixture(autouse=True)
def reset_chico_logger():
    """Remove all handlers from the chico logger before and after each test."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture()
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect chico paths to a temp directory."""
    monkeypatch.setattr("chico.core.log.CHICO_DIR", tmp_path)
    monkeypatch.setattr("chico.core.log.LOG_FILE", tmp_path / "chico.log")
    return tmp_path


class TestJsonFormatter:
    def _make_record(
        self, msg: str, level: int = logging.INFO, extra: dict | None = None
    ) -> logging.LogRecord:
        record = logging.LogRecord(
            name=_LOGGER_NAME,
            level=level,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )
        for key, value in (extra or {}).items():
            setattr(record, key, value)
        return record

    def test_output_is_valid_json(self):
        formatter = _JsonFormatter()
        record = self._make_record("test.event")
        line = formatter.format(record)
        parsed = json.loads(line)
        assert isinstance(parsed, dict)

    def test_contains_required_fields(self):
        formatter = _JsonFormatter()
        record = self._make_record("test.event")
        parsed = json.loads(formatter.format(record))
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "event" in parsed
        assert "message" in parsed

    def test_event_equals_message(self):
        formatter = _JsonFormatter()
        record = self._make_record("plan.started")
        parsed = json.loads(formatter.format(record))
        assert parsed["event"] == "plan.started"
        assert parsed["message"] == "plan.started"

    def test_level_is_uppercase_string(self):
        formatter = _JsonFormatter()
        record = self._make_record("x", level=logging.WARNING)
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "WARNING"

    def test_timestamp_is_iso_format(self):
        formatter = _JsonFormatter()
        record = self._make_record("x")
        parsed = json.loads(formatter.format(record))
        # ISO 8601 timestamps contain 'T' and '+'
        assert "T" in parsed["timestamp"]
        assert "+" in parsed["timestamp"]

    def test_extra_fields_are_included(self):
        formatter = _JsonFormatter()
        record = self._make_record(
            "apply.failed", extra={"resource_id": "r1", "reason": "denied"}
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["resource_id"] == "r1"
        assert parsed["reason"] == "denied"

    def test_exc_info_is_included(self):
        formatter = _JsonFormatter()
        try:
            raise ValueError("oops")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name=_LOGGER_NAME,
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="err",
            args=(),
            exc_info=exc_info,
        )
        parsed = json.loads(formatter.format(record))
        assert "exc_info" in parsed
        assert "ValueError" in parsed["exc_info"]


class TestSetupLogging:
    def test_creates_chico_dir(self, log_dir: Path):
        log_dir_sub = log_dir / "subdir"
        import chico.core.log as log_module

        monkeypatch_dir = log_dir_sub
        # Patch directly in the module
        original_dir = log_module.CHICO_DIR
        original_file = log_module.LOG_FILE
        log_module.CHICO_DIR = monkeypatch_dir
        log_module.LOG_FILE = monkeypatch_dir / "chico.log"
        try:
            setup_logging()
            assert monkeypatch_dir.exists()
        finally:
            log_module.CHICO_DIR = original_dir
            log_module.LOG_FILE = original_file

    def test_creates_log_file(self, log_dir: Path):
        setup_logging()
        logger = logging.getLogger(_LOGGER_NAME)
        logger.info("test.event")
        assert (log_dir / "chico.log").exists()

    def test_log_file_contains_json(self, log_dir: Path):
        setup_logging()
        logger = logging.getLogger(_LOGGER_NAME)
        logger.info("test.event")
        lines = (log_dir / "chico.log").read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event"] == "test.event"

    def test_is_idempotent(self, log_dir: Path):
        setup_logging()
        setup_logging()
        logger = logging.getLogger(_LOGGER_NAME)
        assert len(logger.handlers) == 1

    def test_does_not_propagate(self, log_dir: Path):
        setup_logging()
        logger = logging.getLogger(_LOGGER_NAME)
        assert logger.propagate is False

    def test_multiple_events_appended(self, log_dir: Path):
        setup_logging()
        logger = logging.getLogger(_LOGGER_NAME)
        logger.info("event.one")
        logger.info("event.two")
        lines = (log_dir / "chico.log").read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["event"] == "event.one"
        assert json.loads(lines[1])["event"] == "event.two"

    def test_extra_fields_written_to_file(self, log_dir: Path):
        setup_logging()
        logger = logging.getLogger(_LOGGER_NAME)
        logger.info("init.completed", extra={"chico_dir": "/home/user/.chico"})
        line = (log_dir / "chico.log").read_text().strip()
        parsed = json.loads(line)
        assert parsed["chico_dir"] == "/home/user/.chico"
