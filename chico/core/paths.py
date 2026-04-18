"""Canonical filesystem paths used by chico.

All paths are derived from the user's home directory at import time.
Import these constants instead of constructing paths inline so that
every module agrees on the same locations.

Paths
-----
CHICO_DIR : Path
    Root directory for all chico data — ``~/.chico/``.
CONFIG_FILE : Path
    User configuration file — ``~/.chico/config.yaml``.
STATE_FILE : Path
    Local state store — ``~/.chico/state.json``.
LOG_FILE : Path
    Append-only structured log — ``~/.chico/chico.log``.
"""

from __future__ import annotations

from pathlib import Path

CHICO_DIR: Path = Path.home() / ".chico"
CONFIG_FILE: Path = CHICO_DIR / "config.yaml"
STATE_FILE: Path = CHICO_DIR / "state.json"
LOG_FILE: Path = CHICO_DIR / "chico.log"
