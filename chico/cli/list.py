"""Implementation of the ``chico list`` command.

Displays all configured sources and providers from ``~/.chico/config.yaml``
in a human-readable format.
"""

from __future__ import annotations

import logging

import typer

from chico.core.config import ConfigNotFoundError, load_config

logger = logging.getLogger("chico")


def list_config() -> None:
    """Show all configured sources and providers.

    Loads ``~/.chico/config.yaml`` and prints a summary of every source
    and provider, including their key fields.
    """
    logger.info("list.started")

    try:
        config = load_config()
    except ConfigNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    if not config.providers and not config.sources:
        typer.echo("No providers or sources configured.")
        typer.echo("Edit ~/.chico/config.yaml or run `chico-ai init` to get started.")
        return

    if config.providers:
        typer.echo(f"Providers ({len(config.providers)}):\n")
        for p in config.providers:
            typer.echo(f"  {p.name}")
            typer.echo(f"    type:  {p.type}")
            typer.echo(f"    level: {p.level}")
            if p.path:
                typer.echo(f"    path:  {p.path}")
            typer.echo("")

    if config.sources:
        typer.echo(f"Sources ({len(config.sources)}):\n")
        for s in config.sources:
            typer.echo(f"  {s.name}")
            typer.echo(f"    type:   {s.type}")
            typer.echo(f"    repo:   {s.repo}")
            typer.echo(f"    path:   {s.path}")
            typer.echo(f"    branch: {s.branch}")
            typer.echo(f"    target: {s.target or '(none)'}")
            if s.source_prefix:
                typer.echo(f"    prefix: {s.source_prefix}")
            typer.echo("")
