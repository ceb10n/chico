"""Tests for chico.__main__ (python -m chico entry point)."""

from __future__ import annotations

import runpy
from pathlib import Path
from unittest.mock import patch


def test_main_calls_app():
    main_path = str(Path(__file__).parent.parent / "chico" / "__main__.py")
    with patch("chico.cli.main.app") as mock_app:
        runpy.run_path(main_path, run_name="__main__")
    mock_app.assert_called_once()
