"""Implementation of the ``chico add`` command group.

Provides subcommands for appending sources and providers to an existing
``~/.chico/config.yaml``.

Usage::

    chico-ai add source --repo org/repo --path configs/ --target kiro
    chico-ai add provider --name kiro-local --level project
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer
import yaml

from chico.core.paths import CONFIG_FILE

logger = logging.getLogger("chico")

add_app = typer.Typer(
    name="add",
    help="Add sources or providers to an existing configuration.",
    no_args_is_help=True,
)


def _load_raw_config() -> dict:
    """Load the raw config dict, or exit if the file doesn't exist."""
    if not CONFIG_FILE.exists():
        typer.echo(
            "Error: no config file found. Run `chico-ai init` first.",
            err=True,
        )
        raise typer.Exit(1)
    return yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}


def _save_raw_config(raw: dict) -> None:
    """Write the raw config dict back to disk."""
    CONFIG_FILE.write_text(
        yaml.dump(raw, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


@add_app.command("source")
def add_source(
    repo: str = typer.Option(..., "--repo", help="Repository in org/repo format."),
    path: str = typer.Option(..., "--path", help="Directory path inside the repo."),
    source_type: str = typer.Option(
        "github", "--type", help="Source type. Currently only 'github'."
    ),
    name: str | None = typer.Option(
        None, "--name", help="Source name. Defaults to the repo name."
    ),
    branch: str = typer.Option("main", "--branch", help="Branch to read from."),
    target: str = typer.Option("kiro", "--target", help="Provider name to sync into."),
    source_prefix: str = typer.Option(
        "",
        "--source-prefix",
        help="Prefix to strip from source paths. Defaults to --path.",
    ),
) -> None:
    """Add a source to the existing configuration."""
    if source_type != "github":
        typer.echo(
            f"Error: unsupported source type '{source_type}'. Supported: github",
            err=True,
        )
        raise typer.Exit(1)

    raw = _load_raw_config()
    sources: list[dict] = raw.get("sources", [])

    source_name = name or repo.split("/")[-1]
    existing_names = {s.get("name") for s in sources}
    if source_name in existing_names:
        typer.echo(
            f"Error: source '{source_name}' already exists in config.",
            err=True,
        )
        raise typer.Exit(1)

    sources.append(
        {
            "name": source_name,
            "type": source_type,
            "repo": repo,
            "path": path,
            "source_prefix": source_prefix or path,
            "branch": branch,
            "target": target,
        }
    )
    raw["sources"] = sources
    _save_raw_config(raw)

    logger.info(
        "add.source.completed",
        extra={"source": source_name, "repo": repo, "target": target},
    )
    typer.echo(f"Added source '{source_name}'")
    typer.echo(f"  repo:   {repo}")
    typer.echo(f"  path:   {path}")
    typer.echo(f"  branch: {branch}")
    typer.echo(f"  target: {target}")


@add_app.command("provider")
def add_provider(
    name: str = typer.Option(..., "--name", help="Unique provider name."),
    provider_type: str = typer.Option(
        "kiro", "--type", help="Provider type. Currently only 'kiro'."
    ),
    level: str = typer.Option(
        "global",
        "--level",
        help="'global' for ~/.kiro/, 'project' for a specific directory.",
    ),
    path: str | None = typer.Option(
        None,
        "--path",
        help="Target directory (project level). Defaults to {cwd}/.kiro when level is 'project'.",
    ),
) -> None:
    """Add a provider to the existing configuration."""
    if provider_type != "kiro":
        typer.echo(
            f"Error: unsupported provider type '{provider_type}'. Supported: kiro",
            err=True,
        )
        raise typer.Exit(1)

    raw = _load_raw_config()
    providers: list[dict] = raw.get("providers", [])

    existing_names = {p.get("name") for p in providers}
    if name in existing_names:
        typer.echo(
            f"Error: provider '{name}' already exists in config.",
            err=True,
        )
        raise typer.Exit(1)

    provider_entry: dict = {"name": name, "type": provider_type, "level": level}
    if level == "project":
        provider_entry["path"] = path or str(Path.cwd() / ".kiro")

    providers.append(provider_entry)
    raw["providers"] = providers
    _save_raw_config(raw)

    logger.info(
        "add.provider.completed",
        extra={"provider": name, "level": level},
    )
    typer.echo(f"Added provider '{name}'")
    typer.echo(f"  type:  {provider_type}")
    typer.echo(f"  level: {level}")
    if "path" in provider_entry:
        typer.echo(f"  path:  {provider_entry['path']}")
