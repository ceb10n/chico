"""Tests for chico.core.apply."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chico.core.apply import ApplyResult, execute_apply
from chico.core.config import Config, PolicyConfig, ProviderConfig, SourceConfig
from chico.core.plan import Plan, RiskLevel
from chico.core.resource import ChangeType, Diff, Resource, Result, ResultStatus
from chico.core.source import FetchResult

# ── helpers ───────────────────────────────────────────────────────────────────


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
    def __init__(self, name: str, result: FetchResult) -> None:
        self._name = name
        self._result = result

    def fetch(self) -> FetchResult:
        return self._result


class _OkResource:
    """Resource that always reports a diff and applies successfully."""

    def __init__(self, resource_id: str) -> None:
        self._id = resource_id

    @property
    def resource_id(self) -> str:
        return self._id

    def desired_state(self) -> dict:
        return {"content": "desired"}

    def current_state(self) -> dict:
        return {}

    def diff(self) -> Diff:
        return Diff(change_type=ChangeType.ADD, resource_id=self._id)

    def apply(self) -> Result:
        return Result(status=ResultStatus.OK, resource_id=self._id)


class _ErrorResource:
    """Resource that always reports a diff and fails to apply."""

    def __init__(self, resource_id: str) -> None:
        self._id = resource_id

    @property
    def resource_id(self) -> str:
        return self._id

    def desired_state(self) -> dict:
        return {"content": "desired"}

    def current_state(self) -> dict:
        return {}

    def diff(self) -> Diff:
        return Diff(change_type=ChangeType.ADD, resource_id=self._id)

    def apply(self) -> Result:
        return Result(
            status=ResultStatus.ERROR,
            resource_id=self._id,
            message="Permission denied",
        )


class _SyncedResource:
    """Resource that reports no diff (already in sync)."""

    def __init__(self, resource_id: str) -> None:
        self._id = resource_id

    @property
    def resource_id(self) -> str:
        return self._id

    def desired_state(self) -> dict:
        return {"content": "same"}

    def current_state(self) -> dict:
        return {"content": "same"}

    def diff(self) -> Diff:
        return Diff(change_type=ChangeType.NONE, resource_id=self._id)

    def apply(self) -> Result:  # pragma: no cover — must never be called
        raise AssertionError("apply() called on a synced resource")


class _StubProvider:
    def __init__(self, resources: list[Resource]) -> None:
        self._resources = resources

    def list_resources(self) -> list[Resource]:
        return self._resources


# ── ApplyResult ───────────────────────────────────────────────────────────────


class TestApplyResult:
    def _plan(self) -> Plan:
        return Plan(plan_id="x", changes=[], risk_level=RiskLevel.NONE)

    def test_ok_count(self):
        results = [
            Result(status=ResultStatus.OK, resource_id="a"),
            Result(status=ResultStatus.ERROR, resource_id="b", message="oops"),
        ]
        ar = ApplyResult(plan=self._plan(), results=results)
        assert ar.ok_count == 1

    def test_error_count(self):
        results = [
            Result(status=ResultStatus.OK, resource_id="a"),
            Result(status=ResultStatus.ERROR, resource_id="b", message="oops"),
        ]
        ar = ApplyResult(plan=self._plan(), results=results)
        assert ar.error_count == 1

    def test_has_errors_true(self):
        results = [Result(status=ResultStatus.ERROR, resource_id="a", message="x")]
        ar = ApplyResult(plan=self._plan(), results=results)
        assert ar.has_errors is True

    def test_has_errors_false(self):
        results = [Result(status=ResultStatus.OK, resource_id="a")]
        ar = ApplyResult(plan=self._plan(), results=results)
        assert ar.has_errors is False

    def test_ok_count_all_ok(self):
        results = [
            Result(status=ResultStatus.OK, resource_id="a"),
            Result(status=ResultStatus.OK, resource_id="b"),
        ]
        ar = ApplyResult(plan=self._plan(), results=results)
        assert ar.ok_count == 2
        assert ar.error_count == 0

    def test_empty_results(self):
        ar = ApplyResult(plan=self._plan(), results=[])
        assert ar.ok_count == 0
        assert ar.error_count == 0
        assert ar.has_errors is False


# ── execute_apply ─────────────────────────────────────────────────────────────


@pytest.fixture()
def state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    sf = tmp_path / "state.json"
    monkeypatch.setattr("chico.core.state.STATE_FILE", sf)
    return sf


class TestExecuteApply:
    def test_empty_config_returns_empty_result(self, state_file):
        result = execute_apply(_make_config())
        assert result.results == []
        assert result.plan.changes == []

    def test_applies_changed_resources(self, monkeypatch, tmp_path, state_file):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        resource = _OkResource("/some/file.md")
        monkeypatch.setattr(
            "chico.core.apply._build_source",
            lambda cfg: _StubSource(cfg.name, FetchResult(version="abc", files={})),
        )
        monkeypatch.setattr(
            "chico.core.apply._build_provider",
            lambda *_: _StubProvider([resource]),
        )

        result = execute_apply(config)
        assert len(result.results) == 1
        assert result.results[0].ok

    def test_synced_resources_are_not_applied(self, monkeypatch, state_file):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        resource = _SyncedResource("/some/file.md")
        monkeypatch.setattr(
            "chico.core.apply._build_source",
            lambda cfg: _StubSource(cfg.name, FetchResult(version="abc", files={})),
        )
        monkeypatch.setattr(
            "chico.core.apply._build_provider",
            lambda *_: _StubProvider([resource]),
        )

        result = execute_apply(config)
        assert result.results == []

    def test_source_without_provider_is_skipped(self, monkeypatch, state_file):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="missing"
        )
        provider_cfg = ProviderConfig(name="other", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        monkeypatch.setattr(
            "chico.core.apply._build_source",
            lambda cfg: _StubSource(cfg.name, FetchResult(version="abc", files={})),
        )

        result = execute_apply(config)
        assert result.results == []

    def test_error_result_does_not_stop_other_applies(self, monkeypatch, state_file):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        resources: list[Resource] = [
            _ErrorResource("/fail.md"),
            _OkResource("/ok.md"),
        ]
        monkeypatch.setattr(
            "chico.core.apply._build_source",
            lambda cfg: _StubSource(cfg.name, FetchResult(version="abc", files={})),
        )
        monkeypatch.setattr(
            "chico.core.apply._build_provider",
            lambda *_: _StubProvider(resources),
        )

        result = execute_apply(config)
        assert result.ok_count == 1
        assert result.error_count == 1

    def test_records_source_version_in_state(self, monkeypatch, state_file):
        source_cfg = SourceConfig(
            name="my-source", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        monkeypatch.setattr(
            "chico.core.apply._build_source",
            lambda cfg: _StubSource(
                cfg.name, FetchResult(version="sha-abc123", files={})
            ),
        )
        monkeypatch.setattr(
            "chico.core.apply._build_provider",
            lambda *_: _StubProvider([]),
        )

        execute_apply(config)

        saved = json.loads(state_file.read_text())
        assert saved["versions"]["my-source"] == "sha-abc123"

    def test_updates_last_run_in_state(self, monkeypatch, state_file):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        resource = _OkResource("/some/file.md")
        monkeypatch.setattr(
            "chico.core.apply._build_source",
            lambda cfg: _StubSource(cfg.name, FetchResult(version="abc", files={})),
        )
        monkeypatch.setattr(
            "chico.core.apply._build_provider",
            lambda *_: _StubProvider([resource]),
        )

        execute_apply(config)

        saved = json.loads(state_file.read_text())
        assert saved["last_run"] is not None
        assert "timestamp" in saved["last_run"]
        assert saved["last_run"]["applied"] == 1
        assert saved["last_run"]["errors"] == 0

    def test_records_resource_results_in_state(self, monkeypatch, state_file):
        source_cfg = SourceConfig(
            name="s", type="github", repo="o/r", path="p/", target="kiro"
        )
        provider_cfg = ProviderConfig(name="kiro", type="kiro", level="global")
        config = _make_config(sources=[source_cfg], providers=[provider_cfg])

        resource = _OkResource("/some/file.md")
        monkeypatch.setattr(
            "chico.core.apply._build_source",
            lambda cfg: _StubSource(cfg.name, FetchResult(version="abc", files={})),
        )
        monkeypatch.setattr(
            "chico.core.apply._build_provider",
            lambda *_: _StubProvider([resource]),
        )

        execute_apply(config)

        saved = json.loads(state_file.read_text())
        assert len(saved["resources"]) == 1
        assert saved["resources"][0]["resource_id"] == "/some/file.md"
        assert saved["resources"][0]["status"] == "ok"
        assert saved["resources"][0]["source"] == "s"

    def test_plan_id_is_uuid_format(self, state_file):
        result = execute_apply(_make_config())
        assert len(result.plan.plan_id) == 36
        assert result.plan.plan_id.count("-") == 4

    def test_apply_new_file_on_disk(self, monkeypatch, tmp_path, state_file):
        """Integration: real KiroProvider writes the file to disk."""
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
            "chico.core.apply._build_source",
            lambda cfg: _StubSource(cfg.name, fetch_result),
        )
        monkeypatch.setattr("chico.core.apply._resolve_kiro_dir", lambda _: kiro_dir)

        result = execute_apply(config)

        assert result.ok_count == 1
        assert (kiro_dir / "steering" / "product.md").read_text() == "# Product"
