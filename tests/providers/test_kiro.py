"""Tests for chico.providers.kiro."""

from __future__ import annotations

from pathlib import Path

from chico.core.resource import ChangeType, ResultStatus
from chico.core.source import FetchResult
from chico.providers.kiro import KiroFileResource, KiroProvider

# ---------------------------------------------------------------------------
# KiroFileResource
# ---------------------------------------------------------------------------


class TestKiroFileResourceIdentity:
    def test_resource_id_is_local_path(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        r = KiroFileResource(
            source_path="steering/product.md",
            source_content="# Product",
            local_path=local,
        )
        assert r.resource_id == str(local)


class TestKiroFileResourceDesiredState:
    def test_returns_source_content(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        r = KiroFileResource("steering/product.md", "# Product", local)
        assert r.desired_state() == {"content": "# Product"}


class TestKiroFileResourceCurrentState:
    def test_returns_empty_dict_when_file_missing(self, tmp_path: Path):
        local = tmp_path / "steering" / "missing.md"
        r = KiroFileResource("steering/missing.md", "# x", local)
        assert r.current_state() == {}

    def test_returns_file_content_when_present(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        local.parent.mkdir(parents=True)
        local.write_text("# Existing content")
        r = KiroFileResource("steering/product.md", "# New", local)
        assert r.current_state() == {"content": "# Existing content"}

    def test_reads_latin1_encoded_file(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        local.parent.mkdir(parents=True)
        local.write_bytes("configuração".encode("latin-1"))
        r = KiroFileResource("steering/product.md", "# New", local)
        assert r.current_state() == {"content": "configuração"}


class TestKiroFileResourceDiff:
    def test_diff_is_add_when_file_missing(self, tmp_path: Path):
        local = tmp_path / "steering" / "new.md"
        r = KiroFileResource("steering/new.md", "# New", local)
        diff = r.diff()
        assert diff.change_type == ChangeType.ADD
        assert diff.has_changes is True

    def test_diff_is_none_when_content_matches(self, tmp_path: Path):
        local = tmp_path / "steering" / "same.md"
        local.parent.mkdir(parents=True)
        local.write_text("# Same")
        r = KiroFileResource("steering/same.md", "# Same", local)
        diff = r.diff()
        assert diff.change_type == ChangeType.NONE
        assert diff.has_changes is False

    def test_diff_is_modify_when_content_differs(self, tmp_path: Path):
        local = tmp_path / "steering" / "changed.md"
        local.parent.mkdir(parents=True)
        local.write_text("# Old content")
        r = KiroFileResource("steering/changed.md", "# New content", local)
        diff = r.diff()
        assert diff.change_type == ChangeType.MODIFY
        assert diff.has_changes is True

    def test_diff_modify_includes_field_change(self, tmp_path: Path):
        local = tmp_path / "steering" / "changed.md"
        local.parent.mkdir(parents=True)
        local.write_text("# Old")
        r = KiroFileResource("steering/changed.md", "# New", local)
        diff = r.diff()
        assert "content" in diff.changes
        assert diff.changes["content"].from_value == "# Old"
        assert diff.changes["content"].to_value == "# New"

    def test_diff_resource_id_matches(self, tmp_path: Path):
        local = tmp_path / "steering" / "f.md"
        r = KiroFileResource("steering/f.md", "x", local)
        diff = r.diff()
        assert diff.resource_id == str(local)


class TestKiroFileResourceApply:
    def test_apply_creates_file(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        r = KiroFileResource("steering/product.md", "# Product", local)
        result = r.apply()
        assert local.exists()
        assert local.read_text() == "# Product"
        assert result.status == ResultStatus.OK

    def test_apply_creates_parent_dirs(self, tmp_path: Path):
        local = tmp_path / "a" / "b" / "c" / "product.md"
        r = KiroFileResource("a/b/c/product.md", "# x", local)
        r.apply()
        assert local.exists()

    def test_apply_overwrites_existing_file(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        local.parent.mkdir(parents=True)
        local.write_text("# Old")
        r = KiroFileResource("steering/product.md", "# New", local)
        r.apply()
        assert local.read_text() == "# New"

    def test_apply_returns_ok_result(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        r = KiroFileResource("steering/product.md", "# x", local)
        result = r.apply()
        assert result.ok is True
        assert result.resource_id == str(local)

    def test_apply_returns_error_on_permission_failure(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        local.parent.mkdir(parents=True)
        local.parent.chmod(0o444)  # read-only dir
        r = KiroFileResource("steering/product.md", "# x", local)
        result = r.apply()
        assert result.status == ResultStatus.ERROR
        assert result.message != ""
        local.parent.chmod(0o755)  # restore so tmp_path cleanup works

    def test_apply_is_idempotent(self, tmp_path: Path):
        local = tmp_path / "steering" / "product.md"
        r = KiroFileResource("steering/product.md", "# x", local)
        r.apply()
        result = r.apply()
        assert result.ok is True
        assert local.read_text() == "# x"


# ---------------------------------------------------------------------------
# KiroProvider
# ---------------------------------------------------------------------------


class TestKiroProviderName:
    def test_name_is_kiro(self, tmp_path: Path):
        provider = KiroProvider(
            fetch_result=FetchResult(version="abc", files={}),
            kiro_dir=tmp_path,
        )
        assert provider.name == "kiro"


class TestKiroProviderListResources:
    def test_returns_one_resource_per_file(self, tmp_path: Path):
        fetch = FetchResult(
            version="abc123",
            files={
                "steering/product.md": "# Product",
                "steering/tech.md": "# Tech",
            },
        )
        provider = KiroProvider(fetch_result=fetch, kiro_dir=tmp_path)
        resources = provider.list_resources()
        assert len(resources) == 2

    def test_returns_empty_list_when_no_files(self, tmp_path: Path):
        provider = KiroProvider(
            fetch_result=FetchResult(version="abc", files={}),
            kiro_dir=tmp_path,
        )
        assert provider.list_resources() == []

    def test_maps_source_path_to_kiro_dir(self, tmp_path: Path):
        fetch = FetchResult(
            version="abc",
            files={"steering/product.md": "# Product"},
        )
        provider = KiroProvider(fetch_result=fetch, kiro_dir=tmp_path)
        resource = provider.list_resources()[0]
        assert resource.resource_id == str(tmp_path / "steering" / "product.md")

    def test_strips_source_prefix_from_path(self, tmp_path: Path):
        fetch = FetchResult(
            version="abc",
            files={"configs/steering/product.md": "# Product"},
        )
        provider = KiroProvider(
            fetch_result=fetch,
            kiro_dir=tmp_path,
            source_prefix="configs/",
        )
        resource = provider.list_resources()[0]
        assert resource.resource_id == str(tmp_path / "steering" / "product.md")

    def test_desired_state_matches_source_content(self, tmp_path: Path):
        fetch = FetchResult(
            version="abc",
            files={"steering/product.md": "# Product content"},
        )
        provider = KiroProvider(fetch_result=fetch, kiro_dir=tmp_path)
        resource = provider.list_resources()[0]
        assert resource.desired_state() == {"content": "# Product content"}

    def test_agents_md_is_included(self, tmp_path: Path):
        fetch = FetchResult(
            version="abc",
            files={
                "steering/product.md": "# Product",
                "steering/AGENTS.md": "# Agents",
            },
        )
        provider = KiroProvider(fetch_result=fetch, kiro_dir=tmp_path)
        ids = [r.resource_id for r in provider.list_resources()]
        assert any("AGENTS.md" in rid for rid in ids)

    def test_is_valid_provider(self, tmp_path: Path):
        from chico.core.provider import Provider

        provider = KiroProvider(
            fetch_result=FetchResult(version="abc", files={}),
            kiro_dir=tmp_path,
        )
        assert isinstance(provider, Provider)
