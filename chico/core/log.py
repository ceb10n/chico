"""Structured JSON logging for chico.

All chico actions are logged as newline-delimited JSON to ``~/.chico/chico.log``.
Each entry includes a timestamp, level, event name, and message, plus any extra
fields passed at the call site.

Usage
-----
Obtain the shared logger in any module::

    import logging
    logger = logging.getLogger("chico")

    logger.info("plan.started", extra={"source": "core-config"})
    logger.error("apply.failed", extra={"resource_id": "kiro.prompt.base", "reason": str(e)})

Setup
-----
Call :func:`setup_logging` once at CLI startup (done automatically by the Typer
callback in ``chico.cli.main``). After that, every ``getLogger("chico")`` call
returns the same configured logger.

Log format
----------
Each line is a JSON object with at least::

    {
      "timestamp": "2024-01-15T10:30:00.123456+00:00",
      "level": "INFO",
      "event": "init.completed",
      "message": "init.completed"
    }

Extra keyword arguments passed via ``extra={}`` are merged into the top-level
object::

    {
      "timestamp": "2024-01-15T10:30:00.123456+00:00",
      "level": "ERROR",
      "event": "apply.failed",
      "message": "apply.failed",
      "resource_id": "kiro.prompt.base",
      "reason": "permission denied"
    }
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from chico.core.paths import CHICO_DIR, LOG_FILE

# Rotate at 5 MB, keep the 3 most recent archives alongside the active file.
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

_LOGGER_NAME = "chico"

# Fields injected by the logging machinery that we do not want to forward.
_SKIP_FIELDS = frozenset(
    {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class _JsonFormatter(logging.Formatter):
    """Format each log record as a single JSON object on one line."""

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "event": record.message,
            "message": record.message,
        }

        # Merge any extra fields supplied via extra={...}
        for key, value in record.__dict__.items():
            if key not in _SKIP_FIELDS:
                entry[key] = value

        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


def setup_logging(level: int = logging.DEBUG) -> None:
    """Configure the shared ``"chico"`` logger to write JSON to the log file.

    Creates ``~/.chico/`` if it does not yet exist (e.g. before ``chico init``
    has been run). The active log file is ``~/.chico/chico.log``; when it
    reaches 5 MB it is rotated to ``chico.log.1``, ``chico.log.2``, etc., up
    to 3 archives before the oldest is discarded.

    Parameters
    ----------
    level:
        The minimum log level to capture. Defaults to ``logging.DEBUG`` so
        that all events are recorded to the file regardless of severity.

    Notes
    -----
    Safe to call multiple times — subsequent calls are no-ops because the
    logger already has handlers attached.
    """
    logger = logging.getLogger(_LOGGER_NAME)

    if logger.handlers:
        return

    CHICO_DIR.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(_JsonFormatter())

    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
