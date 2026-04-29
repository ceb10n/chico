"""Configuration model and loader for chico.

Reads ``~/.chico/config.yaml`` and produces typed configuration objects
that the plan engine uses to instantiate sources and providers.

Config file location: ``~/.chico/config.yaml`` (created by ``chico init``).

Example config
--------------
::

    providers:
      - name: kiro
        type: kiro
        level: global           # "global" (~/.kiro) or "project" (.kiro/)

    sources:
      - name: kiro-configs
        type: github
        repo: org/kiro-config
        path: configs/
        branch: main            # optional, default: main
        token_env: GITHUB_TOKEN # optional, default: GITHUB_TOKEN
        source_prefix: configs/ # optional, strip before mapping to kiro_dir
        target: kiro            # optional, which provider to sync into

    policy:
      strategy: safe            # "safe" requires manual apply; "auto" applies immediately

Usage
-----
::

    from chico.core.config import load_config

    config = load_config()
    source_cfg = config.get_source("kiro-configs")
    provider_cfg = config.get_provider("kiro")
"""

from __future__ import annotations

from dataclasses import dataclass

import yaml

from chico.core.paths import CONFIG_FILE


class ConfigNotFoundError(Exception):
    """Raised when ``~/.chico/config.yaml`` does not exist.

    Run ``chico init`` to create the default configuration file.
    """


class ConfigValidationError(Exception):
    """Raised when the config file is missing required fields or has invalid values."""


@dataclass
class SourceConfig:
    """Configuration for a single source.

    Attributes
    ----------
    name:
        Unique source name, referenced by ``target`` in provider configs.
    type:
        Source type. Currently only ``"github"`` is supported.
    repo:
        Full GitHub repository name in ``org/repo`` format.
    path:
        Directory (or file) path inside the repository to fetch from.
    branch:
        Branch to read from. Defaults to ``"main"``.
    token_env:
        Name of the environment variable holding the GitHub token.
        Defaults to ``"GITHUB_TOKEN"``. Token resolution also tries
        ``gh auth token`` and unauthenticated access automatically.
    source_prefix:
        Prefix to strip from source paths before mapping to the local
        provider directory. For example, ``"configs/"`` maps
        ``configs/steering/product.md`` → ``steering/product.md``.
    target:
        Name of the provider this source syncs into.
    """

    name: str
    type: str
    repo: str
    path: str
    branch: str = "main"
    token_env: str = "GITHUB_TOKEN"
    source_prefix: str = ""
    target: str = ""


@dataclass
class ProviderConfig:
    """Configuration for a single provider.

    Attributes
    ----------
    name:
        Unique provider name.
    type:
        Provider type. Currently only ``"kiro"`` is supported.
    level:
        Kiro directory scope. ``"global"`` targets ``~/.kiro/``;
        ``"project"`` targets ``.kiro/`` in a specific project directory.
        Defaults to ``"global"``.
    path:
        Absolute path to the target directory. Only used when ``level``
        is ``"project"``. When set, chico syncs files directly into this
        path — no ``.kiro/`` suffix is appended. This gives the user full
        control over the target directory and avoids double-nesting when
        the source files already live under ``.kiro/`` in the repository.
        When omitted and ``level`` is ``"project"``, falls back to
        ``{cwd}/.kiro``.
    """

    name: str
    type: str
    level: str = "global"
    path: str = ""


@dataclass
class PolicyConfig:
    """Reconciliation policy settings.

    Attributes
    ----------
    strategy:
        ``"safe"`` — always require explicit ``chico apply`` (default).
        ``"auto"`` — apply immediately after plan (used by the scheduler).
    """

    strategy: str = "safe"


@dataclass
class Config:
    """The full parsed contents of ``~/.chico/config.yaml``.

    Attributes
    ----------
    providers:
        List of configured providers.
    sources:
        List of configured sources.
    policy:
        Reconciliation policy settings.
    """

    providers: list[ProviderConfig]
    sources: list[SourceConfig]
    policy: PolicyConfig

    def get_provider(self, name: str) -> ProviderConfig | None:
        """Return the provider with the given name, or ``None``."""
        return next((p for p in self.providers if p.name == name), None)

    def get_source(self, name: str) -> SourceConfig | None:
        """Return the source with the given name, or ``None``."""
        return next((s for s in self.sources if s.name == name), None)

    def filter_by_source(self, source_name: str) -> Config:
        """Return a new Config containing only the named source.

        Raises
        ------
        ConfigValidationError
            If no source with the given name exists.
        """
        filtered = [s for s in self.sources if s.name == source_name]
        if not filtered:
            available = ", ".join(s.name for s in self.sources) or "(none)"
            raise ConfigValidationError(
                f"Source {source_name!r} not found. Available sources: {available}"
            )
        return Config(providers=self.providers, sources=filtered, policy=self.policy)


def load_config() -> Config:
    """Load and validate ``~/.chico/config.yaml``.

    Returns
    -------
    Config
        The fully parsed configuration.

    Raises
    ------
    ConfigNotFoundError
        If the config file does not exist. Run ``chico init`` to create it.
    ConfigValidationError
        If the config file is missing required fields.
    """
    if not CONFIG_FILE.exists():
        raise ConfigNotFoundError(
            f"Config file not found: {CONFIG_FILE}\n"
            "Run `chico init` to create the default configuration."
        )

    raw = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}

    providers = [_parse_provider(p) for p in raw.get("providers", [])]
    sources = [_parse_source(s) for s in raw.get("sources", [])]
    policy = _parse_policy(raw.get("policy", {}))

    return Config(providers=providers, sources=sources, policy=policy)


def _parse_source(raw: dict) -> SourceConfig:
    for required in ("name", "type", "repo", "path"):
        if required not in raw:
            raise ConfigValidationError(
                f"Source entry is missing required field '{required}': {raw}"
            )
    return SourceConfig(
        name=raw["name"],
        type=raw["type"],
        repo=raw["repo"],
        path=raw["path"],
        branch=raw.get("branch", "main"),
        token_env=raw.get("token_env", "GITHUB_TOKEN"),
        source_prefix=raw.get("source_prefix", ""),
        target=raw.get("target", ""),
    )


def _parse_provider(raw: dict) -> ProviderConfig:
    return ProviderConfig(
        name=raw["name"],
        type=raw["type"],
        level=raw.get("level", "global"),
        path=raw.get("path", ""),
    )


def _parse_policy(raw: dict) -> PolicyConfig:
    return PolicyConfig(strategy=raw.get("strategy", "safe"))
