"""Entry point for the chico CLI.

All Typer commands are registered here. Each command's logic lives in its own
module under ``chico/cli/`` and is imported here to keep this file thin.
"""

from __future__ import annotations

from typing import Annotated

import typer

from chico.cli.add import add_app
from chico.cli.apply import apply as _apply
from chico.cli.diff import diff as _diff
from chico.cli.init import init as _init
from chico.cli.list import list_config as _list
from chico.cli.plan import plan as _plan
from chico.cli.schedule import schedule_app
from chico.cli.status import status as _status
from chico.cli.sync import sync as _sync
from chico.core.log import setup_logging

app = typer.Typer(
    name="chico-ai",
    help="Sync agent configuration files from GitHub to your local environment.",
    no_args_is_help=True,
)


@app.callback()
def callback() -> None:
    """chico-ai — keep your AI agent configuration in sync with a GitHub repository."""
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
    source_prefix: Annotated[
        str,
        typer.Option(
            "--source-prefix",
            help="Prefix to strip from source paths when mapping to local files. Defaults to --path.",
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
    """Set up chico-ai for the first time.

    Creates ~/.chico/config.yaml and ~/.chico/state.json. Pass --source,
    --repo, and --path to generate a ready-to-use config pointing at your
    GitHub repository. Safe to run more than once — exits cleanly if already
    initialized.
    """
    _init(
        source=source,
        repo=repo,
        path=path,
        source_prefix=source_prefix,
        target=target,
        level=level,
        branch=branch,
    )


@app.command()
def plan(
    source: Annotated[
        str | None,
        typer.Argument(
            help="Source name to plan. Omit to plan all sources.",
        ),
    ] = None,
) -> None:
    """Preview which files would be added or updated — without touching anything.

    Optionally pass a source name to scope the plan to a single source.
    """
    _plan(source=source)


@app.command()
def apply(
    source: Annotated[
        str | None,
        typer.Argument(
            help="Source name to apply. Omit to apply all sources.",
        ),
    ] = None,
) -> None:
    """Download files from GitHub and write them to ~/.kiro/.

    Optionally pass a source name to scope the apply to a single source.
    """
    _apply(source=source)


@app.command()
def diff(
    source: Annotated[
        str | None,
        typer.Argument(
            help="Source name to diff. Omit to diff all sources.",
        ),
    ] = None,
) -> None:
    """Show the exact content differences for each file that would change.

    Optionally pass a source name to scope the diff to a single source.
    """
    _diff(source=source)


@app.command()
def status() -> None:
    """Show the last sync result and which files are being managed.

    Reads ~/.chico/state.json and prints when the last apply ran, which
    GitHub commit was last synced, and how many files are tracked.
    """
    _status()


@app.command(name="list")
def list_cmd() -> None:
    """Show all configured sources and providers."""
    _list()


@app.command()
def sync(
    source: Annotated[
        str | None,
        typer.Argument(
            help="Source name to sync. Omit to sync all sources.",
        ),
    ] = None,
) -> None:
    """Sync now — fetch from GitHub and update ~/.kiro/ in one step.

    Optionally pass a source name to scope the sync to a single source.
    """
    _sync(source=source)


app.add_typer(add_app)
app.add_typer(schedule_app)


if __name__ == "__main__":  # pragma: no cover
    app()
