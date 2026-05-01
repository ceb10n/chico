"""Implementation of the ``chico list`` command.

Displays all configured sources and providers from ``~/.chico/config.yaml``
in a human-readable format.
"""

from __future__ import annotations

import logging

import typer
from rich.markup import escape

from chico.cli.output import get_console, get_err_console
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
        get_err_console().print(f"[bold red]Error:[/bold red] {escape(str(exc))}")
        raise typer.Exit(1) from exc

    console = get_console()

    if not config.providers and not config.sources:
        console.print("[dim]No providers or sources configured.[/dim]")
        console.print(
            "[dim]Edit ~/.chico/config.yaml or run `chico-ai init` to get started.[/dim]"
        )
        return

    if config.providers:
        console.print(f"[bold]Providers ({len(config.providers)}):[/bold]\n")
        for p in config.providers:
            console.print(f"  [bold]{escape(p.name)}[/bold]")
            console.print(f"    [dim]type:[/dim]  {escape(p.type)}")
            console.print(f"    [dim]level:[/dim] {escape(p.level)}")
            if p.path:
                console.print(f"    [dim]path:[/dim]  {escape(p.path)}")
            console.print("")

    if config.sources:
        console.print(f"[bold]Sources ({len(config.sources)}):[/bold]\n")
        for s in config.sources:
            console.print(f"  [bold]{escape(s.name)}[/bold]")
            console.print(f"    [dim]type:[/dim]   {escape(s.type)}")
            console.print(f"    [dim]repo:[/dim]   {escape(s.repo)}")
            console.print(f"    [dim]path:[/dim]   {escape(s.path)}")
            console.print(f"    [dim]branch:[/dim] {escape(s.branch)}")
            console.print(f"    [dim]target:[/dim] {escape(s.target) or '(none)'}")
            if s.source_prefix:
                console.print(f"    [dim]prefix:[/dim] {escape(s.source_prefix)}")
            console.print("")
