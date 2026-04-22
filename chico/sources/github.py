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

import logging
import os
import subprocess
from typing import cast

from github import Github
from github.ContentFile import ContentFile

from chico.core.source import FetchResult, SourceFetchError

_DEFAULT_TOKEN_ENV = "GITHUB_TOKEN"

logger = logging.getLogger("chico")


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
        logger.info(
            "github.fetch.started",
            extra={"repo": self._repo, "path": self._path, "branch": self._branch},
        )
        token = self._resolve_token()

        try:
            gh = Github(token)
            repo = gh.get_repo(self._repo)
            branch = repo.get_branch(self._branch)
            commit_sha = branch.commit.sha

            logger.info(
                "github.fetch.branch",
                extra={"branch": self._branch, "sha": commit_sha},
            )

            files: dict[str, str] = {}
            queue: list[ContentFile] = []

            raw = repo.get_contents(self._path, ref=commit_sha)
            queue.extend(
                cast(list[ContentFile], raw)
                if isinstance(raw, list)
                else [cast(ContentFile, raw)]
            )

            while queue:
                item = queue.pop()
                if item.type == "dir":
                    logger.info(
                        "github.fetch.descending",
                        extra={"dir": item.path},
                    )
                    nested = repo.get_contents(item.path, ref=commit_sha)
                    queue.extend(
                        cast(list[ContentFile], nested)
                        if isinstance(nested, list)
                        else [cast(ContentFile, nested)]
                    )
                else:
                    raw_bytes = item.decoded_content
                    try:
                        files[item.path] = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        files[item.path] = raw_bytes.decode("latin-1")
                        logger.info(
                            "github.fetch.encoding_fallback",
                            extra={"file": item.path, "encoding": "latin-1"},
                        )

            logger.info(
                "github.fetch.completed",
                extra={
                    "repo": self._repo,
                    "version": commit_sha,
                    "file_count": len(files),
                    "files": list(files.keys()),
                },
            )

            return FetchResult(version=commit_sha, files=files)

        except Exception as exc:
            logger.error(
                "github.fetch.error",
                extra={"repo": self._repo, "path": self._path, "error": str(exc)},
            )
            raise SourceFetchError(str(exc)) from exc

    def _resolve_token(self) -> str | None:
        """Resolve the GitHub token using the fallback chain.

        Returns ``None`` when no token is found — unauthenticated requests
        are passed through to PyGithub, which works for public repositories.
        """
        if self._token:
            logger.info("github.token.resolved", extra={"method": "explicit"})
            return self._token

        env_token = os.environ.get(self._token_env)
        if env_token:
            logger.info(
                "github.token.resolved",
                extra={"method": "env", "var": self._token_env},
            )
            return env_token

        cli_token = _gh_cli_token()
        if cli_token:
            logger.info("github.token.resolved", extra={"method": "gh_cli"})
            return cli_token

        logger.info("github.token.resolved", extra={"method": "none"})
        return None
