"""Tests for chico.core.plan."""

from __future__ import annotations

from pathlib import Path

import pytest

from chico.core.config import Config, PolicyConfig, ProviderConfig, SourceConfig
from chico.core.plan import (
    Plan,
    RiskLevel,
    _build_provider,
    _build_source,
    _compute_risk_level,
    _resolve_kiro_dir,
    compute_plan,
)
from chico.core.resource import ChangeType, Diff, FieldChange
from chico.core.source import FetchResult

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_config(
    sources: list[SourceConfig] | None = None,
    providers: list[ProviderConfig] | None = None,
) -> Config:
    return Config(
        providers=providers or [],
        sources=sources or [],
        policy=PolicyConfig(),
    )


class _StubSource:
    def __init__(self, result: FetchResult) -> None:
        self._result = result

    def fetch(self) -> FetchResult:
        return self._result


# ── Plan dataclass ────────────────────────────────────────────────────────────


class TestPlan:
    def test_has_changes_true(self):
        diff = Diff(change_type=ChangeType.ADD, resource_id="some/file")
        p = Plan(plan_id="x", changes=[diff], risk_level=RiskLevel.LOW)
        assert p.has_changes is True

    def test_has_changes_false(self):
        p = Plan(plan_id="x", changes=[], risk_level=RiskLevel.NONE)
        assert p.has_changes is False

    def test_plan_id_is_stored(self):
        p = Plan(plan_id="abc-123", changes=[], risk_level=RiskLevel.NONE)
        assert p.plan_id == "abc-123"

    def test_changes_and_risk_level_stored(self):
        diff = Diff(change_type=ChangeType.MODIFY, resource_id="f")
        p = Plan(plan_id="x", changes=[diff], risk_level=RiskLevel.MEDIUM)
        assert p.changes == [diff]
        assert p.risk_level == RiskLevel.MEDIUM


# ── _compute_risk_level ───────────────────────────────────────────────────────


class TestComputeRiskLevel:
    def test_none_when_no_changes(self):
        assert _compute_risk_level([]) == RiskLevel.NONE

    def test_low_for_only_adds(self):
        changes = [Diff(change_type=ChangeType.ADD, resource_id="a")]
        assert _compute_risk_level(changes) == RiskLevel.LOW

    def test_medium_for_modify(self):
        changes = [
            Diff(change_type=ChangeType.ADD, resource_id="a"),
            Diff(
                change_type=ChangeType.MODIFY,
                resource_id="b",
                changes={"content": FieldChange("old", "new")},
            ),
        ]
        assert _compute_risk_level(changes) == RiskLevel.MEDIUM

    def test_high_for_remove(self):
        changes = [Diff(change_type=ChangeType.REMOVE, resource_id="a")]
        assert _compute_risk_level(changes) == RiskLevel.HIGH

    def test_high_takes_precedence_over_modify(self):
        changes = [
            Diff(change_type=ChangeType.MODIFY, resource_id="a"),
            Diff(change_type=ChangeType.REMOVE, resource_id="b"),
        ]
        assert _compute_risk_level(changes) == RiskLevel.HIGH


# ── _build_source ─────────────────────────────────────────────────────────────


class TestBuildSource:
    def test_returns_github_source_for_github_type(self):
        from chico.sources.github import GitHubSource

        cfg = SourceConfig(name="s", type="github", repo="org/repo", path="configs/")
        source = _build_source(cfg)
        assert isinstance(source, GitHubSource)

    def test_raises_for_unknown_type(self):
        cfg = SourceConfig(name="s", type="s3", repo="bucket", path="prefix/")
        with pytest.raises(ValueError, match="s3"):
            _build_source(cfg)


# ── _build_provider ───────────────────────────────────────────────────────────


class TestBuildProvider:
    def test_returns_kiro_provider_for_kiro_type(self, tmp_path):
        from chico.providers.kiro import KiroProvider

        cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        fetch_result = FetchResult(version="abc", files={})
        provider = _build_provider(cfg, fetch_result, "", tmp_path / ".kiro")
        assert isinstance(provider, KiroProvider)

    def test_raises_for_unknown_type(self, tmp_path):
        cfg = ProviderConfig(name="p", type="unknown")
        fetch_result = FetchResult(version="abc", files={})
        with pytest.raises(ValueError, match="unknown"):
            _build_provider(cfg, fetch_result, "", tmp_path / ".kiro")


# ── _resolve_kiro_dir ─────────────────────────────────────────────────────────


class TestResolveKiroDir:
    def test_global_returns_home_kiro(self):
        cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        assert _resolve_kiro_dir(cfg) == Path.home() / ".kiro"

    def test_project_without_path_returns_cwd_kiro(self):
        cfg = ProviderConfig(name="kiro", type="kiro", level="project")
        assert _resolve_kiro_dir(cfg) == Path.cwd() / ".kiro"

    def test_project_with_path_returns_configured_path_directly(self, tmp_path):
        target = str(tmp_path / ".kiro")
        cfg = ProviderConfig(name="kiro", type="kiro", level="project", path=target)
        assert _resolve_kiro_dir(cfg) == Path(target)

    def test_global_ignores_path(self, tmp_path):
        cfg = ProviderConfig(
            name="kiro", type="kiro", level="global", path=str(tmp_path)
        )
        assert _resolve_kiro_dir(cfg) == Path.home() / ".kiro"


# ── compute_plan ──────────────────────────────────────────────────────────────


class TestComputePlan:
    def test_empty_config_returns_empty_plan(self):
        plan = compute_plan(_make_config())
        assert plan.changes == []
        assert plan.risk_level == RiskLevel.NONE

    def test_plan_id_is_uuid_format(self):
        plan = compute_plan(_make_config())
        assert len(plan.plan_id) == 36
        assert plan.plan_id.count("-") == 4

    def test_source_without_matching_provider_is_skipped(self, monkeypatch):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="missing"
        )
        provider_cfg = ProviderConfig(name="other", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        fetch_result = FetchResult(version="abc", files={"p/file.md": "content"})
        monkeypatch.setattr(
            "chico.core.plan._build_source", lambda _: _StubSource(fetch_result)
        )

        plan = compute_plan(config)
        assert plan.changes == []

    def test_add_change_when_file_is_new(self, monkeypatch, tmp_path):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        kiro_dir = tmp_path / ".kiro"
        fetch_result = FetchResult(
            version="abc", files={"steering/product.md": "# Product"}
        )
        monkeypatch.setattr(
            "chico.core.plan._build_source", lambda _: _StubSource(fetch_result)
        )
        monkeypatch.setattr("chico.core.plan._resolve_kiro_dir", lambda _: kiro_dir)

        plan = compute_plan(config)
        assert len(plan.changes) == 1
        assert plan.changes[0].change_type == ChangeType.ADD
        assert plan.risk_level == RiskLevel.LOW

    def test_no_change_when_file_matches(self, monkeypatch, tmp_path):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        kiro_dir = tmp_path / ".kiro"
        content = "# Product\n"
        (kiro_dir / "steering").mkdir(parents=True)
        (kiro_dir / "steering" / "product.md").write_text(content)

        fetch_result = FetchResult(
            version="abc", files={"steering/product.md": content}
        )
        monkeypatch.setattr(
            "chico.core.plan._build_source", lambda _: _StubSource(fetch_result)
        )
        monkeypatch.setattr("chico.core.plan._resolve_kiro_dir", lambda _: kiro_dir)

        plan = compute_plan(config)
        assert plan.changes == []
        assert plan.risk_level == RiskLevel.NONE

    def test_modify_change_when_file_differs(self, monkeypatch, tmp_path):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        kiro_dir = tmp_path / ".kiro"
        (kiro_dir / "steering").mkdir(parents=True)
        (kiro_dir / "steering" / "product.md").write_text("# Old Content")

        fetch_result = FetchResult(
            version="abc", files={"steering/product.md": "# New Content"}
        )
        monkeypatch.setattr(
            "chico.core.plan._build_source", lambda _: _StubSource(fetch_result)
        )
        monkeypatch.setattr("chico.core.plan._resolve_kiro_dir", lambda _: kiro_dir)

        plan = compute_plan(config)
        assert len(plan.changes) == 1
        assert plan.changes[0].change_type == ChangeType.MODIFY
        assert plan.risk_level == RiskLevel.MEDIUM

    def test_multiple_files_aggregated(self, monkeypatch, tmp_path):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        kiro_dir = tmp_path / ".kiro"
        fetch_result = FetchResult(
            version="abc",
            files={
                "steering/a.md": "content-a",
                "steering/b.md": "content-b",
            },
        )
        monkeypatch.setattr(
            "chico.core.plan._build_source", lambda _: _StubSource(fetch_result)
        )
        monkeypatch.setattr("chico.core.plan._resolve_kiro_dir", lambda _: kiro_dir)

        plan = compute_plan(config)
        assert len(plan.changes) == 2

    def test_multiple_sources_aggregated(self, monkeypatch, tmp_path):
        s1 = SourceConfig(
            name="s1", type="github", repo="o/r1", path="p/", target="kiro"
        )
        s2 = SourceConfig(
            name="s2", type="github", repo="o/r2", path="q/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[s1, s2], providers=[provider_cfg])

        kiro_dir = tmp_path / ".kiro"
        fr1 = FetchResult(version="abc", files={"file1.md": "c1"})
        fr2 = FetchResult(version="def", files={"file2.md": "c2"})

        def _stub(cfg: SourceConfig) -> _StubSource:
            return _StubSource(fr1 if cfg.name == "s1" else fr2)

        monkeypatch.setattr("chico.core.plan._build_source", _stub)
        monkeypatch.setattr("chico.core.plan._resolve_kiro_dir", lambda _: kiro_dir)

        plan = compute_plan(config)
        assert len(plan.changes) == 2
