"""Implementation of the chico init command."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import cast

import typer
import yaml

from chico.core.paths import CHICO_DIR, CONFIG_FILE, STATE_FILE

logger = logging.getLogger("chico")

_DEFAULT_CONFIG: dict = {
    "providers": [],
    "sources": [],
    "policy": {"strategy": "safe"},
}

_DEFAULT_STATE: dict = {
    "status": "idle",
    "last_run": None,
    "resources": [],
    "versions": {},
}


def init(
    source: str | None = None,
    repo: str | None = None,
    path: str = "",
    source_prefix: str = "",
    target: str = "kiro",
    level: str = "global",
    branch: str = "main",
) -> None:
    """Initialise the chico home directory."""
    logger.info("init.started")
    if CONFIG_FILE.exists():
        logger.info("init.already_initialized", extra={"chico_dir": str(CHICO_DIR)})
        typer.echo(f"Already initialized at {CHICO_DIR}")
        raise typer.Exit()
    if source is not None:
        if source != "github":
            typer.echo(
                f"Error: unsupported source type \'{source}\'. Supported: github",
                err=True,
            )
            raise typer.Exit(1)
        if repo is None:
            typer.echo("Error: --repo is required when --source is specified", err=True)
            raise typer.Exit(1)
        if not path:
            typer.echo("Error: --path is required when --source is specified", err=True)
            raise typer.Exit(1)
    CHICO_DIR.mkdir(parents=True, exist_ok=True)
    if source is not None:
        repo = cast(str, repo)
        source_name = repo.split("/")[-1]
        provider_entry: dict = {"name": target, "type": "kiro", "level": level}
        if level == "project":
            provider_entry["path"] = str(Path.cwd() / ".kiro")
        config: dict = {
            "providers": [provider_entry],
            "sources": [
                {
                    "name": source_name,
                    "type": source,
                    "repo": repo,
                    "path": path,
                    "source_prefix": source_prefix or path,
                    "branch": branch,
                    "target": target,
                }
            ],
            "policy": {"strategy": "safe"},
        }
    else:
        config = _DEFAULT_CONFIG
    CONFIG_FILE.write_text(
        yaml.dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8"
    )
    STATE_FILE.write_text(json.dumps(_DEFAULT_STATE, indent=2), encoding="utf-8")
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
    if source is not None:
        typer.echo(f"  source  {repo} ({source})")
    typer.echo("")
    typer.echo("Next steps:")
    if source is None:
        typer.echo(f"  1. Edit {CONFIG_FILE} to add providers and sources")
        typer.echo("  2. Run `chico plan` to preview changes")
        typer.echo("  3. Run `chico apply` to apply them")
    else:
        typer.echo("  1. Run `chico plan` to preview changes")
        typer.echo("  2. Run `chico apply` to apply them")
