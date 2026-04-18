"""Entry point for the chico CLI.

All Typer commands are registered here. Each command's logic lives in its own
module under ``chico/cli/`` and is imported here to keep this file thin.
"""

from __future__ import annotations

import typer

from chico.cli.init import init as _init
from chico.core.log import setup_logging

app = typer.Typer(
    name="chico",
    help="Agent-native configuration control plane.",
    no_args_is_help=True,
)


@app.callback()
def callback() -> None:
    """chico — reconcile agent configuration state across environments."""
    setup_logging()


@app.command()
def init() -> None:
    """Initialize chico in ~/.chico/.

    Creates the chico home directory with a default config.yaml and an empty
    state.json. Safe to run multiple times — exits cleanly if already set up.
    """
    _init()


if __name__ == "__main__":  # pragma: no cover
    app()
