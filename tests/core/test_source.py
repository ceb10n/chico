"""Tests for chico.core.source."""

from __future__ import annotations

from chico.core.source import FetchResult, Source


class TestFetchResult:
    def test_stores_version_and_files(self):
        result = FetchResult(version="abc123", files={"config.yaml": "key: value"})
        assert result.version == "abc123"
        assert result.files == {"config.yaml": "key: value"}

    def test_files_defaults_to_empty_dict(self):
        result = FetchResult(version="abc123")
        assert result.files == {}

    def test_files_are_independent_between_instances(self):
        r1 = FetchResult(version="a")
        r2 = FetchResult(version="b")
        r1.files["x"] = "y"
        assert "x" not in r2.files

    def test_version_is_string(self):
        result = FetchResult(version="deadbeef")
        assert isinstance(result.version, str)


class TestSourceProtocol:
    def test_valid_implementation_is_instance(self):
        class MySource:
            @property
            def name(self) -> str:
                return "my-source"

            def fetch(self) -> FetchResult:
                return FetchResult(version="abc123", files={})

        assert isinstance(MySource(), Source)

    def test_missing_fetch_is_not_instance(self):
        class NoFetch:
            @property
            def name(self) -> str:
                return "x"

        assert not isinstance(NoFetch(), Source)

    def test_missing_name_is_not_instance(self):
        class NoName:
            def fetch(self) -> FetchResult:
                return FetchResult(version="abc123")

        assert not isinstance(NoName(), Source)

    def test_fetch_returns_fetch_result(self):
        class MySource:
            @property
            def name(self) -> str:
                return "my-source"

            def fetch(self) -> FetchResult:
                return FetchResult(
                    version="abc123",
                    files={"steering.md": "# Steering"},
                )

        result = MySource().fetch()
        assert isinstance(result, FetchResult)
        assert result.version == "abc123"
        assert result.files["steering.md"] == "# Steering"
