"""Apply engine for chico.

Fetches desired state from every configured source, diffs it against local
state, applies all changes, and persists the result to ``~/.chico/state.json``.

Example usage::

    from chico.core.config import load_config
    from chico.core.apply import execute_apply

    config = load_config()
    result = execute_apply(config)

    print(f"Applied {result.ok_count}, {result.error_count} error(s).")
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from chico.core.config import Config
from chico.core.plan import (
    Plan,
    _build_provider,
    _build_source,
    _compute_risk_level,
    _resolve_kiro_dir,
)
from chico.core.resource import Diff, Resource, Result, ResultStatus
from chico.core.state import load_state, save_state

logger = logging.getLogger("chico")


@dataclass
class ApplyResult:
    """The outcome of ``execute_apply``.

    Attributes
    ----------
    plan:
        The computed changeset that was applied.
    results:
        One :class:`~chico.core.resource.Result` per resource that had a
        change. Resources already in sync are excluded.
    """

    plan: Plan
    results: list[Result] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        """Number of resources applied successfully."""
        return sum(1 for r in self.results if r.ok)

    @property
    def error_count(self) -> int:
        """Number of resources that failed to apply."""
        return sum(1 for r in self.results if r.status == ResultStatus.ERROR)

    @property
    def has_errors(self) -> bool:
        """Return ``True`` if at least one resource failed to apply."""
        return self.error_count > 0


def execute_apply(config: Config) -> ApplyResult:
    """Fetch desired state, apply all changes, and persist state.

    For every source declared in ``config``, fetches the desired state,
    computes a diff, and calls :meth:`~chico.core.resource.Resource.apply`
    on every resource that has changes. Updates ``~/.chico/state.json``
    with the versions and results afterwards.

    Parameters
    ----------
    config:
        The loaded chico configuration.

    Returns
    -------
    ApplyResult
        The plan that was executed and the per-resource results.

    Raises
    ------
    SourceFetchError
        If any source fails to fetch the desired state.
    ValueError
        If a source or provider type declared in the config is not supported.
    """
    all_changes: list[Diff] = []
    source_versions: dict[str, str] = {}
    to_apply: list[tuple[Resource, str]] = []

    for source_cfg in config.sources:
        source = _build_source(source_cfg)
        fetch_result = source.fetch()
        source_versions[source_cfg.name] = fetch_result.version

        provider_cfg = config.get_provider(source_cfg.target)
        if provider_cfg is None:
            continue

        kiro_dir = _resolve_kiro_dir(provider_cfg.level)
        provider = _build_provider(
            provider_cfg, fetch_result, source_cfg.source_prefix, kiro_dir
        )

        for resource in provider.list_resources():
            diff = resource.diff()
            if diff.has_changes:
                all_changes.append(diff)
                to_apply.append((resource, source_cfg.name))

    plan = Plan(
        plan_id=str(uuid.uuid4()),
        changes=all_changes,
        risk_level=_compute_risk_level(all_changes),
    )

    results: list[Result] = []
    for resource, _ in to_apply:
        result = resource.apply()
        results.append(result)
        if result.ok:
            logger.info(
                "resource.apply.ok", extra={"resource_id": resource.resource_id}
            )
        else:
            logger.error(
                "resource.apply.error",
                extra={"resource_id": resource.resource_id, "detail": result.message},
            )

    _persist_state(plan, results, source_versions)

    return ApplyResult(plan=plan, results=results)


def _persist_state(
    plan: Plan,
    results: list[Result],
    source_versions: dict[str, str],
) -> None:
    """Write apply results and source versions to state."""
    state = load_state()

    for source_name, version in source_versions.items():
        state.record_version(source_name, version)

    ok = sum(1 for r in results if r.ok)
    errors = sum(1 for r in results if r.status == ResultStatus.ERROR)

    state.last_run = {
        "timestamp": datetime.now(UTC).isoformat(),
        "plan_id": plan.plan_id,
        "applied": ok,
        "errors": errors,
    }
    state.resources = [
        {
            "resource_id": r.resource_id,
            "status": str(r.status),
            "message": r.message,
        }
        for r in results
    ]

    save_state(state)
