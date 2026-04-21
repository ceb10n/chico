"""Entry point for the chico CLI.

All Typer commands are registered here. Each command's logic lives in its own
module under ``chico/cli/`` and is imported here to keep this file thin.
"""

from __future__ import annotations

from typing import Annotated

import typer

from chico.cli.apply import apply as _apply
from chico.cli.diff import diff as _diff
from chico.cli.init import init as _init
from chico.cli.plan import plan as _plan
from chico.cli.status import status as _status
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
def init(
    source: Annotated[
        str | None,
        typer.Option("--source", help="Source type to configure (e.g. github)."),
    ] = None,
    repo: Annotated[
        str | None,
        typer.Option("--repo", help="Repository in org/repo format."),
    ] = None,
    path: Annotated[
        str,
        typer.Option(
            "--path", help="Directory path inside the repository to fetch from."
        ),
    ] = "",
    target: Annotated[
        str,
        typer.Option("--target", help="Provider name to sync into."),
    ] = "kiro",
    level: Annotated[
        str,
        typer.Option(
            "--level", help="Kiro level: global (~/.kiro) or project (.kiro/)."
        ),
    ] = "global",
    branch: Annotated[
        str,
        typer.Option("--branch", help="Branch to read from."),
    ] = "main",
) -> None:
    """Initialize chico in ~/.chico/.

    Creates the chico home directory with a config.yaml and an empty
    state.json. Pass --source, --repo, and --path to pre-populate the config
    with a real source and provider. Safe to run multiple times — exits
    cleanly if already set up.
    """
    _init(
        source=source, repo=repo, path=path, target=target, level=level, branch=branch
    )


@app.command()
def plan() -> None:
    """Preview changes between desired and current state.

    Fetches desired state from all configured sources and diffs it against
    the current local state. Prints a summary of what would change without
    writing anything to disk.
    """
    _plan()


@app.command()
def apply() -> None:
    """Apply changes between desired and current state.

    Fetches desired state from all configured sources, applies every change
    to the local Kiro directory, and records the outcome in state.json.
    """
    _apply()


@app.command()
def diff() -> None:
    """Show field-level differences between desired and current state.

    Fetches desired state from all configured sources and prints a detailed
    breakdown of each change. For modified resources, the before and after
    value of every changed field is shown. Nothing is written to disk.
    """
    _diff()


@app.command()
def status() -> None:
    """Show the current chico state.

    Reads ~/.chico/state.json and prints a summary of the last apply run,
    tracked source versions, and the total number of managed resources.
    """
    _status()


if __name__ == "__main__":  # pragma: no cover
    app()
