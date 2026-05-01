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

from github import (
    BadCredentialsException,
    Github,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)
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


def _is_fine_grained_pat(token: str) -> bool:
    """Return True if token is a fine-grained PAT (github_pat_ prefix)."""
    return token.startswith("github_pat_")


def _auth_error_message(
    repo: str, token_env: str, token: str | None, method: str
) -> str:
    """Build a friendly authentication failure message."""
    fine_grained_note = ""
    if token and _is_fine_grained_pat(token):
        fine_grained_note = (
            "\n\nNote: your token looks like a fine-grained PAT (github_pat_...).\n"
            "Fine-grained PATs must have 'Contents: Read' permission explicitly\n"
            "granted per repository. Classic PATs (ghp_...) with 'repo' scope\n"
            "are more reliable for private repositories."
        )

    return (
        f"Authentication failed for repository '{repo}'.\n\n"
        f"Your GitHub token was rejected. Here is what you can do:\n\n"
        f"  1. Set a valid token:  export {token_env}=<your_token>\n"
        f"  2. Make sure the token has not expired.\n"
        f"  3. For private repos, use a classic PAT with 'repo' scope\n"
        f"     or a fine-grained PAT with 'Contents: Read' permission.\n"
        f"  4. Authenticate via the GitHub CLI:  gh auth login\n"
        f"{fine_grained_note}\n\n"
        f"Token resolved via: {method}"
    )


def _not_found_error_message(
    repo: str, token_env: str, token: str | None, method: str
) -> str:
    """Build a friendly not-found message that surfaces the auth angle."""
    fine_grained_note = ""
    if token and _is_fine_grained_pat(token):
        fine_grained_note = (
            "\n\nNote: your token looks like a fine-grained PAT (github_pat_...).\n"
            "Fine-grained PATs must explicitly list this repository and grant\n"
            "'Contents: Read' permission. Consider using a classic PAT instead."
        )

    return (
        f"Repository '{repo}' was not found.\n\n"
        f"If this is a private repository, this is almost certainly an auth issue —\n"
        f"GitHub returns 404 instead of 403 for private repos to prevent enumeration.\n\n"
        f"Here is what you can do:\n\n"
        f"  1. Set a valid token:  export {token_env}=<your_token>\n"
        f"  2. Make sure the token has 'repo' scope (classic PAT) or\n"
        f"     'Contents: Read' permission (fine-grained PAT) for this repo.\n"
        f"  3. Authenticate via the GitHub CLI:  gh auth login\n"
        f"  4. Double-check the repository name: '{repo}'\n"
        f"{fine_grained_note}\n\n"
        f"Token resolved via: {method}"
    )


def _forbidden_error_message(repo: str, token: str | None, method: str) -> str:
    """Build a friendly 403-forbidden message."""
    if token and _is_fine_grained_pat(token):
        return (
            f"Access denied for repository '{repo}' (HTTP 403).\n\n"
            f"Your fine-grained PAT does not have the required permissions.\n"
            f"Make sure 'Contents: Read' is granted for '{repo}'.\n"
            f"Consider switching to a classic PAT with 'repo' scope.\n\n"
            f"Token resolved via: {method}"
        )
    return (
        f"Access denied for repository '{repo}' (HTTP 403).\n\n"
        f"Your token does not have permission to access this repository.\n"
        f"Make sure your token has 'repo' scope for private repositories.\n\n"
        f"Token resolved via: {method}"
    )


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
        token, method = self._resolve_token()

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

        except BadCredentialsException as exc:
            msg = _auth_error_message(self._repo, self._token_env, token, method)
            logger.error(
                "github.fetch.auth_error", extra={"repo": self._repo, "method": method}
            )
            raise SourceFetchError(msg) from exc

        except UnknownObjectException as exc:
            msg = _not_found_error_message(self._repo, self._token_env, token, method)
            logger.error("github.fetch.not_found", extra={"repo": self._repo})
            raise SourceFetchError(msg) from exc

        except RateLimitExceededException as exc:
            msg = (
                f"GitHub API rate limit exceeded for repository '{self._repo}'. "
                f"Wait a moment and try again."
            )
            logger.error("github.fetch.rate_limit", extra={"repo": self._repo})
            raise SourceFetchError(msg) from exc

        except GithubException as exc:
            if exc.status == 403:
                msg = _forbidden_error_message(self._repo, token, method)
            else:
                msg = f"GitHub API error for repository '{self._repo}' (HTTP {exc.status}): {exc.data}"
            logger.error(
                "github.fetch.api_error",
                extra={"repo": self._repo, "status": exc.status},
            )
            raise SourceFetchError(msg) from exc

        except Exception as exc:
            logger.error(
                "github.fetch.error",
                extra={"repo": self._repo, "path": self._path, "error": str(exc)},
            )
            raise SourceFetchError(str(exc)) from exc

    def _resolve_token(self) -> tuple[str | None, str]:
        """Resolve the GitHub token using the fallback chain.

        Returns ``(token, method)`` where ``method`` describes how the token
        was found — useful for diagnostic messages when auth fails.
        Returns ``(None, "none")`` when no token is found.
        """
        if self._token:
            logger.info("github.token.resolved", extra={"method": "explicit"})
            return self._token, "explicit"

        env_token = os.environ.get(self._token_env)
        if env_token:
            logger.info(
                "github.token.resolved",
                extra={"method": "env", "var": self._token_env},
            )
            return env_token, f"env:{self._token_env}"

        cli_token = _gh_cli_token()
        if cli_token:
            logger.info("github.token.resolved", extra={"method": "gh_cli"})
            return cli_token, "gh_cli"

        logger.info("github.token.resolved", extra={"method": "none"})
        return None, "none"
