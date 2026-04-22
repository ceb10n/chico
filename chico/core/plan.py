"""Plan computation for chico.

A Plan is the computed changeset for a single ``chico plan`` run. It collects
all resource diffs across every source/provider pair declared in the
configuration, assigns a risk level, and provides a stable identifier for
auditing.

Example usage::

    from chico.core.config import load_config
    from chico.core.plan import compute_plan

    config = load_config()
    plan = compute_plan(config)

    if plan.has_changes:
        for diff in plan.changes:
            print(diff.change_type, diff.resource_id)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from chico.core.config import Config, ProviderConfig, SourceConfig
from chico.core.resource import ChangeType, Diff
from chico.core.source import FetchResult
from chico.providers.kiro import KiroProvider
from chico.sources.github import GitHubSource

logger = logging.getLogger("chico")


class RiskLevel(StrEnum):
    """Estimated risk of applying a plan.

    Values
    ------
    NONE:
        No changes — nothing would be modified.
    LOW:
        Only new resources would be created; nothing would be overwritten.
    MEDIUM:
        Existing resources would be modified.
    HIGH:
        Resources would be deleted.
    """

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Plan:
    """A computed changeset produced by ``chico plan``.

    Attributes
    ----------
    plan_id:
        Unique identifier for this plan run (UUID4).
    changes:
        All resource diffs that require an action. Diffs with
        ``ChangeType.NONE`` are excluded.
    risk_level:
        Estimated risk of applying this plan.
    """

    plan_id: str
    changes: list[Diff]
    risk_level: RiskLevel = field(default=RiskLevel.NONE)

    @property
    def has_changes(self) -> bool:
        """Return ``True`` if there is at least one actionable change."""
        return bool(self.changes)


def compute_plan(config: Config) -> Plan:
    """Compute a plan from the given configuration.

    For every source declared in ``config``, fetches the desired state and
    computes a diff against the current local state. Aggregates all diffs
    into a single :class:`Plan`.

    Parameters
    ----------
    config:
        The loaded chico configuration.

    Returns
    -------
    Plan
        The computed changeset. :attr:`Plan.changes` is empty when
        everything is already in sync.

    Raises
    ------
    SourceFetchError
        If any source fails to fetch the desired state.
    ValueError
        If a source or provider type declared in the config is not supported.
    """
    all_changes: list[Diff] = []

    for source_cfg in config.sources:
        logger.info(
            "plan.source.processing",
            extra={
                "source": source_cfg.name,
                "repo": source_cfg.repo,
                "path": source_cfg.path,
                "branch": source_cfg.branch,
                "target": source_cfg.target,
            },
        )
        source = _build_source(source_cfg)
        fetch_result = source.fetch()

        provider_cfg = config.get_provider(source_cfg.target)
        if provider_cfg is None:
            logger.warning(
                "plan.provider.not_found",
                extra={"source": source_cfg.name, "target": source_cfg.target},
            )
            continue

        kiro_dir = _resolve_kiro_dir(provider_cfg.level)
        logger.info(
            "plan.provider.found",
            extra={"provider": provider_cfg.name, "kiro_dir": str(kiro_dir)},
        )
        provider = _build_provider(
            provider_cfg, fetch_result, source_cfg.source_prefix, kiro_dir
        )

        resources = provider.list_resources()
        logger.info(
            "plan.resources.listed",
            extra={"source": source_cfg.name, "count": len(resources)},
        )

        for resource in resources:
            diff = resource.diff()
            logger.info(
                "plan.resource.diff",
                extra={
                    "resource_id": resource.resource_id,
                    "change_type": str(diff.change_type),
                },
            )
            if diff.has_changes:
                all_changes.append(diff)

    return Plan(
        plan_id=str(uuid.uuid4()),
        changes=all_changes,
        risk_level=_compute_risk_level(all_changes),
    )


def _compute_risk_level(changes: list[Diff]) -> RiskLevel:
    """Derive a :class:`RiskLevel` from a list of diffs."""
    if not changes:
        return RiskLevel.NONE
    types = {d.change_type for d in changes}
    if ChangeType.REMOVE in types:
        return RiskLevel.HIGH
    if ChangeType.MODIFY in types:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _resolve_kiro_dir(level: str) -> Path:
    """Return the kiro directory path for the given provider level."""
    if level == "global":
        return Path.home() / ".kiro"
    return Path.cwd() / ".kiro"


def _build_source(cfg: SourceConfig) -> GitHubSource:
    """Instantiate a source from its configuration."""
    if cfg.type == "github":
        return GitHubSource(
            name=cfg.name,
            repo=cfg.repo,
            path=cfg.path,
            branch=cfg.branch,
            token_env=cfg.token_env,
        )
    raise ValueError(f"Unsupported source type: {cfg.type!r}")


def _build_provider(
    cfg: ProviderConfig,
    fetch_result: FetchResult,
    source_prefix: str,
    kiro_dir: Path,
) -> KiroProvider:
    """Instantiate a provider from its configuration."""
    if cfg.type == "kiro":
        return KiroProvider(
            fetch_result=fetch_result,
            kiro_dir=kiro_dir,
            source_prefix=source_prefix,
        )
    raise ValueError(f"Unsupported provider type: {cfg.type!r}")
