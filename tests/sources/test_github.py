"""Tests for chico.sources.github.GitHubSource."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chico.core.source import FetchResult, SourceFetchError
from chico.sources.github import GitHubSource, _gh_cli_token


def _make_github_mock(commit_sha: str, files: dict[str, str]) -> MagicMock:
    """Build a PyGithub mock tree that returns the given files."""
    github = MagicMock()
    repo = MagicMock()
    branch = MagicMock()
    branch.commit.sha = commit_sha
    github.get_repo.return_value = repo
    repo.get_branch.return_value = branch

    def get_contents(path, ref=None):
        if path in files:
            content = MagicMock()
            content.type = "file"
            content.path = path
            content.decoded_content = files[path].encode()
            return content
        results = []
        for file_path, file_content in files.items():
            if file_path.startswith(path.rstrip("/") + "/") or path == "":
                item = MagicMock()
                item.type = "file"
                item.path = file_path
                item.decoded_content = file_content.encode()
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
