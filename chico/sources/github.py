"""GitHub source for chico.

Fetches desired-state files from a path inside a private (or public) GitHub
repository. The full commit SHA of the branch HEAD is used as the version
identifier and recorded in state after a successful apply.

Authentication
--------------
Token resolution follows this chain — the first match wins:

1. ``token=`` argument passed directly to :class:`GitHubSource` (useful in tests).
2. The environment variable named by ``token_env`` (default: ``GITHUB_TOKEN``).
3. Output of ``gh auth token`` — the GitHub CLI credential cache.
4. No token (unauthenticated). Works for public repositories; private
   repositories will fail at fetch time with a :exc:`~chico.core.source.SourceFetchError`.

Never put a token value directly in ``~/.chico/config.yaml``. Use an
environment variable instead.

Example config
--------------
::

    sources:
      - name: kiro-configs
        type: github
        repo: org/kiro-config
        path: configs/
        branch: main
        token_env: GITHUB_TOKEN   # optional — defaults to GITHUB_TOKEN
        source_prefix: configs/
        target: kiro
"""

from __future__ import annotations

import os
import subprocess
from typing import cast

from github import Github
from github.ContentFile import ContentFile

from chico.core.source import FetchResult, SourceFetchError

_DEFAULT_TOKEN_ENV = "GITHUB_TOKEN"


def _gh_cli_token() -> str | None:
    """Return the token from the GitHub CLI cache, or ``None`` if unavailable."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


class GitHubSource:
    """Fetches files from a GitHub repository path.

    Parameters
    ----------
    name:
        Unique source name, matching the entry in ``config.yaml``.
    repo:
        Full repository name in ``org/repo`` format.
    path:
        Directory path (or file path) inside the repository to fetch from.
    branch:
        Branch to read from. Defaults to ``"main"``.
    token:
        GitHub personal access token. When provided, skips all other
        token resolution steps. Intended for testing.
    token_env:
        Name of the environment variable to read the token from.
        Defaults to ``"GITHUB_TOKEN"``. Ignored when ``token=`` is set.
    """

    def __init__(
        self,
        name: str,
        repo: str,
        path: str,
        branch: str = "main",
        token: str | None = None,
        token_env: str = _DEFAULT_TOKEN_ENV,
    ) -> None:
        self._name = name
        self._repo = repo
        self._path = path
        self._branch = branch
        self._token = token
        self._token_env = token_env

    @property
    def name(self) -> str:
        """Unique name identifying this source."""
        return self._name

    def fetch(self) -> FetchResult:
        """Fetch all files from the configured repository path.

        Returns a :class:`~chico.core.source.FetchResult` whose ``version``
        is the full SHA of the branch HEAD commit at the time of the fetch.

        Token resolution order: explicit ``token=`` arg → env var →
        ``gh auth token`` CLI → unauthenticated.

        Raises
        ------
        SourceFetchError
            If the GitHub API call fails (network error, auth failure,
            missing repository, etc.).
        """
        token = self._resolve_token()

        try:
            gh = Github(token)
            repo = gh.get_repo(self._repo)
            branch = repo.get_branch(self._branch)
            commit_sha = branch.commit.sha

            raw = repo.get_contents(self._path, ref=commit_sha)
            contents = (
                cast(list[ContentFile], raw)
                if isinstance(raw, list)
                else [cast(ContentFile, raw)]
            )

            files = {
                item.path: item.decoded_content.decode()
                for item in contents
                if item.type == "file"
            }

            return FetchResult(version=commit_sha, files=files)

        except Exception as exc:
            raise SourceFetchError(str(exc)) from exc

    def _resolve_token(self) -> str | None:
        """Resolve the GitHub token using the fallback chain.

        Returns ``None`` when no token is found — unauthenticated requests
        are passed through to PyGithub, which works for public repositories.
        """
        if self._token:
            return self._token

        env_token = os.environ.get(self._token_env)
        if env_token:
            return env_token

        return _gh_cli_token()
