"""Tests for chico.sources.github.GitHubSource."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chico.core.source import FetchResult, SourceFetchError
from chico.sources.github import GitHubSource, _gh_cli_token


def _make_github_mock(commit_sha: str, files: dict[str, str]) -> MagicMock:
    """Build a PyGithub mock that simulates the real directory structure.

    Each call to ``get_contents(path)`` returns only the *immediate* children
    of that path — files as ``type="file"`` and subdirectories as
    ``type="dir"``, mirroring the real GitHub Contents API behaviour.
    """
    github = MagicMock()
    repo = MagicMock()
    branch = MagicMock()
    branch.commit.sha = commit_sha
    github.get_repo.return_value = repo
    repo.get_branch.return_value = branch

    def get_contents(path, ref=None):
        path = path.rstrip("/")

        if path in files:
            item = MagicMock()
            item.type = "file"
            item.path = path
            item.decoded_content = files[path].encode()
            return item

        prefix = f"{path}/" if path else ""
        seen: dict[str, str] = {}
        for file_path in files:
            if not file_path.startswith(prefix):
                continue
            remainder = file_path[len(prefix) :]
            if "/" in remainder:
                child = prefix + remainder.split("/")[0]
                seen[child] = "dir"
            else:
                seen[file_path] = "file"

        results = []
        for child_path, child_type in seen.items():
            item = MagicMock()
            item.type = child_type
            item.path = child_path
            if child_type == "file":
                item.decoded_content = files[child_path].encode()
            results.append(item)
        return results

    repo.get_contents.side_effect = get_contents
    return github


class TestGhCliToken:
    def test_returns_token_when_gh_succeeds(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "gh-token-value\n"
        with patch("chico.sources.github.subprocess.run", return_value=mock_result):
            assert _gh_cli_token() == "gh-token-value"

    def test_returns_none_when_gh_returns_empty(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "   "
        with patch("chico.sources.github.subprocess.run", return_value=mock_result):
            assert _gh_cli_token() is None

    def test_returns_none_when_gh_fails(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("chico.sources.github.subprocess.run", return_value=mock_result):
            assert _gh_cli_token() is None

    def test_returns_none_when_gh_not_installed(self):
        with patch(
            "chico.sources.github.subprocess.run", side_effect=FileNotFoundError
        ):
            assert _gh_cli_token() is None

    def test_returns_none_on_timeout(self):
        import subprocess

        with patch(
            "chico.sources.github.subprocess.run",
            side_effect=subprocess.TimeoutExpired("gh", 5),
        ):
            assert _gh_cli_token() is None


class TestGitHubSourceName:
    def test_name_returns_configured_name(self):
        source = GitHubSource(name="kiro-configs", repo="org/repo", path="configs/")
        assert source.name == "kiro-configs"


class TestGitHubSourceFetch:
    def test_returns_fetch_result(self):
        mock_gh = _make_github_mock("abc123", {"configs/steering.md": "# Steering"})
        with patch("chico.sources.github.Github", return_value=mock_gh):
            result = GitHubSource(
                name="s", repo="org/repo", path="configs/", token="t"
            ).fetch()
        assert isinstance(result, FetchResult)

    def test_returns_commit_sha_as_version(self):
        mock_gh = _make_github_mock(
            "abc123def456", {"configs/steering.md": "# Steering"}
        )
        with patch("chico.sources.github.Github", return_value=mock_gh):
            result = GitHubSource(
                name="s", repo="org/repo", path="configs/", token="t"
            ).fetch()
        assert result.version == "abc123def456"

    def test_returns_file_contents(self):
        mock_gh = _make_github_mock(
            "abc123",
            {
                "configs/steering.md": "# Steering content",
                "configs/AGENTS.md": "# Agents",
            },
        )
        with patch("chico.sources.github.Github", return_value=mock_gh):
            result = GitHubSource(
                name="s", repo="org/repo", path="configs/", token="t"
            ).fetch()
        assert result.files["configs/steering.md"] == "# Steering content"
        assert result.files["configs/AGENTS.md"] == "# Agents"

    def test_decodes_latin1_files_when_not_utf8(self):
        mock_gh = MagicMock()
        repo = mock_gh.get_repo.return_value
        repo.get_branch.return_value.commit.sha = "abc"
        item = MagicMock()
        item.type = "file"
        item.path = "configs/readme.md"
        item.decoded_content = "configuração".encode("latin-1")
        repo.get_contents.return_value = item
        with patch("chico.sources.github.Github", return_value=mock_gh):
            result = GitHubSource(
                name="s", repo="org/repo", path="configs/readme.md", token="t"
            ).fetch()
        assert result.files["configs/readme.md"] == "configuração"

    def test_uses_configured_branch(self):
        mock_gh = _make_github_mock("abc", {"configs/f.md": "x"})
        repo = mock_gh.get_repo.return_value
        with patch("chico.sources.github.Github", return_value=mock_gh):
            GitHubSource(
                name="s", repo="org/repo", path="configs/", token="t", branch="develop"
            ).fetch()
        repo.get_branch.assert_called_once_with("develop")

    def test_handles_single_file_path(self):
        mock_gh = MagicMock()
        repo = mock_gh.get_repo.return_value
        repo.get_branch.return_value.commit.sha = "abc123"
        single_file = MagicMock()
        single_file.type = "file"
        single_file.path = "configs/steering.md"
        single_file.decoded_content = b"# Steering"
        repo.get_contents.return_value = single_file
        with patch("chico.sources.github.Github", return_value=mock_gh):
            result = GitHubSource(
                name="s", repo="org/repo", path="configs/steering.md", token="t"
            ).fetch()
        assert result.files["configs/steering.md"] == "# Steering"

    def test_raises_source_fetch_error_on_github_exception(self):
        with patch("chico.sources.github.Github") as mock_github:
            mock_github.return_value.get_repo.side_effect = Exception("network error")
            with pytest.raises(SourceFetchError, match="network error"):
                GitHubSource(
                    name="s", repo="org/repo", path="configs/", token="t"
                ).fetch()

    def test_is_valid_source(self):
        from chico.core.source import Source

        assert isinstance(
            GitHubSource(name="s", repo="org/repo", path="configs/", token="t"), Source
        )

    def test_fetches_files_inside_subdirectories(self):
        mock_gh = _make_github_mock(
            "abc123",
            {
                "root/steering/product.md": "# Product",
                "root/steering/tech.md": "# Tech",
                "root/skills/coding.md": "# Coding",
            },
        )
        with patch("chico.sources.github.Github", return_value=mock_gh):
            result = GitHubSource(
                name="s", repo="org/repo", path="root", token="t"
            ).fetch()
        assert "root/steering/product.md" in result.files
        assert "root/steering/tech.md" in result.files
        assert "root/skills/coding.md" in result.files
        assert len(result.files) == 3

    def test_fetches_files_from_nested_directories(self):
        mock_gh = _make_github_mock(
            "sha999",
            {
                "root/a/b/deep.md": "deep content",
                "root/a/shallow.md": "shallow content",
            },
        )
        with patch("chico.sources.github.Github", return_value=mock_gh):
            result = GitHubSource(
                name="s", repo="org/repo", path="root", token="t"
            ).fetch()
        assert result.files["root/a/b/deep.md"] == "deep content"
        assert result.files["root/a/shallow.md"] == "shallow content"

    def test_does_not_include_directory_entries_in_files(self):
        mock_gh = _make_github_mock(
            "abc",
            {"root/steering/product.md": "# Product"},
        )
        with patch("chico.sources.github.Github", return_value=mock_gh):
            result = GitHubSource(
                name="s", repo="org/repo", path="root", token="t"
            ).fetch()
        assert all("." in k.split("/")[-1] for k in result.files)


class TestGitHubSourceTokenResolution:
    def test_explicit_token_takes_priority(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        mock_gh = _make_github_mock("abc", {"configs/f.md": "x"})
        with patch("chico.sources.github.Github") as mock_github:
            mock_github.return_value = mock_gh
            GitHubSource(
                name="s", repo="org/repo", path="configs/", token="explicit-token"
            ).fetch()
        mock_github.assert_called_once_with("explicit-token")

    def test_token_env_var_used_when_no_explicit_token(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        mock_gh = _make_github_mock("abc", {"configs/f.md": "x"})
        with patch("chico.sources.github.Github") as mock_github:
            mock_github.return_value = mock_gh
            GitHubSource(name="s", repo="org/repo", path="configs/").fetch()
        mock_github.assert_called_once_with("env-token")

    def test_custom_token_env_var_name(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MY_GH_TOKEN", "custom-token")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_gh = _make_github_mock("abc", {"configs/f.md": "x"})
        with patch("chico.sources.github.Github") as mock_github:
            mock_github.return_value = mock_gh
            GitHubSource(
                name="s", repo="org/repo", path="configs/", token_env="MY_GH_TOKEN"
            ).fetch()
        mock_github.assert_called_once_with("custom-token")

    def test_gh_cli_token_used_as_fallback(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_gh = _make_github_mock("abc", {"configs/f.md": "x"})
        with (
            patch("chico.sources.github.Github") as mock_github,
            patch("chico.sources.github._gh_cli_token", return_value="gh-cli-token"),
        ):
            mock_github.return_value = mock_gh
            GitHubSource(name="s", repo="org/repo", path="configs/").fetch()
        mock_github.assert_called_once_with("gh-cli-token")

    def test_unauthenticated_when_no_token_available(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_gh = _make_github_mock("abc", {"configs/f.md": "x"})
        with (
            patch("chico.sources.github.Github") as mock_github,
            patch("chico.sources.github._gh_cli_token", return_value=None),
        ):
            mock_github.return_value = mock_gh
            GitHubSource(name="s", repo="org/repo", path="configs/").fetch()
        mock_github.assert_called_once_with(None)
