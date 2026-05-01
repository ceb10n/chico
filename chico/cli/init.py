"""Implementation of the ``chico init`` command.

Initialises the chico home directory (``~/.chico/``) with a default
configuration file and an empty state file. Running ``chico init`` more than
once is safe — it exits cleanly without overwriting existing data.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import cast

import typer
import yaml
from rich.markup import escape

from chico.cli.output import get_console, get_err_console
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


def init(
    source: str | None = None,
    repo: str | None = None,
    path: str = "",
    source_prefix: str = "",
    target: str = "kiro",
    level: str = "global",
    branch: str = "main",
) -> None:
    """Initialise the chico home directory.

    Creates ``~/.chico/`` and writes two files:

    * ``config.yaml`` — the user configuration. When source flags are
      provided the config is pre-populated with a real provider and source;
      otherwise empty lists are written.
    * ``state.json`` — the local state store, starting idle with no resources.

    If ``~/.chico/`` already exists this function prints a notice and exits
    without modifying any existing files.
    """
    logger.info("init.started")

    console = get_console()

    if CONFIG_FILE.exists():
        logger.info("init.already_initialized", extra={"chico_dir": str(CHICO_DIR)})
        console.print(f"[dim]Already initialized at {escape(str(CHICO_DIR))}[/dim]")
        raise typer.Exit()

    if source is not None:
        if source != "github":
            get_err_console().print(
                f"[bold red]Error:[/bold red] unsupported source type"
                f" {escape(repr(source))}. Supported: github"
            )
            raise typer.Exit(1)
        if repo is None:
            get_err_console().print(
                "[bold red]Error:[/bold red] --repo is required when --source is specified"
            )
            raise typer.Exit(1)
        if not path:
            get_err_console().print(
                "[bold red]Error:[/bold red] --path is required when --source is specified"
            )
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

    console.print(
        f"[green]✓[/green]  Initialized chico at [bold]{escape(str(CHICO_DIR))}[/bold]"
    )
    console.print(f"   [dim]config[/dim]  {escape(str(CONFIG_FILE))}")
    console.print(f"   [dim]state[/dim]   {escape(str(STATE_FILE))}")
    if source is not None:
        console.print(
            f"   [dim]source[/dim]  {escape(cast(str, repo))} ({escape(source)})"
        )
    console.print("")
    console.print("[bold]Next steps:[/bold]")
    if source is None:
        console.print(
            f"   [dim]1.[/dim] Edit {escape(str(CONFIG_FILE))} to add providers and sources"
        )
        console.print("   [dim]2.[/dim] Run `chico plan` to preview changes")
        console.print("   [dim]3.[/dim] Run `chico apply` to apply them")
    else:
        console.print("   [dim]1.[/dim] Run `chico plan` to preview changes")
        console.print("   [dim]2.[/dim] Run `chico apply` to apply them")
