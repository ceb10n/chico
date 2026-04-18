"""Implementation of the ``chico init`` command.

Initialises the chico home directory (``~/.chico/``) with a default
configuration file and an empty state file. Running ``chico init`` more than
once is safe — it exits cleanly without overwriting existing data.
"""

from __future__ import annotations

import json
import logging

import typer
import yaml

from chico.core.paths import CHICO_DIR, CONFIG_FILE, STATE_FILE

logger = logging.getLogger("chico")

_DEFAULT_CONFIG: dict = {
    "providers": [],
    "sources": [],
    "policy": {
        "strategy": "safe",
    },
}

_DEFAULT_STATE: dict = {
    "status": "idle",
    "last_run": None,
    "resources": [],
    "versions": {},
}


def init() -> None:
    """Initialise the chico home directory.

    Creates ``~/.chico/`` and writes two files:

    * ``config.yaml`` — the user configuration, pre-populated with empty
      ``providers`` and ``sources`` lists and a ``safe`` reconciliation policy.
    * ``state.json`` — the local state store, starting idle with no resources.

    If ``~/.chico/`` already exists this function prints a notice and exits
    without modifying any existing files.
    """
    logger.info("init.started")

    if CONFIG_FILE.exists():
        logger.info("init.already_initialized", extra={"chico_dir": str(CHICO_DIR)})
        typer.echo(f"Already initialized at {CHICO_DIR}")
        raise typer.Exit()

    CHICO_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        yaml.dump(_DEFAULT_CONFIG, default_flow_style=False, sort_keys=False)
    )
    STATE_FILE.write_text(json.dumps(_DEFAULT_STATE, indent=2))

    logger.info(
        "init.completed",
        extra={
            "chico_dir": str(CHICO_DIR),
            "config": str(CONFIG_FILE),
            "state": str(STATE_FILE),
        },
    )

    typer.echo(f"Initialized chico at {CHICO_DIR}")
    typer.echo(f"  config  {CONFIG_FILE}")
    typer.echo(f"  state   {STATE_FILE}")
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo(f"  1. Edit {CONFIG_FILE} to add providers and sources")
    typer.echo("  2. Run `chico plan` to preview changes")
    typer.echo("  3. Run `chico apply` to apply them")
