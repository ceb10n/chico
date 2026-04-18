"""Source protocol and FetchResult for chico.

A source is where desired state comes from — a GitHub repository, an S3
bucket, or any future backend. Sources are read-only: they fetch files and
return the version (commit hash, ETag, etc.) that was retrieved.

The fetched version is recorded in ``~/.chico/state.json`` after a successful
apply so that drift can be detected on the next run.

Example usage::

    from chico.core.source import Source, FetchResult

    class MySource:
        @property
        def name(self) -> str:
            return "my-source"

        def fetch(self) -> FetchResult:
            return FetchResult(
                version="abc123def456",
                files={"steering.md": "# Steering file content"},
            )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class FetchResult:
    """The result of fetching desired state from a source.

    Attributes
    ----------
    version:
        An opaque string that uniquely identifies the fetched snapshot.
        For GitHub sources this is the full commit SHA. For S3 it would
        be an ETag or object version ID. Stored in state after apply to
        enable drift detection.
    files:
        A mapping of relative file paths to their text content, as
        fetched from the source.
    """

    version: str
    files: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class Source(Protocol):
    """Protocol that every chico source must satisfy.

    A source knows how to fetch the desired state for a set of files from
    an external system and return the version identifier of what was fetched.

    Implementors do not need to inherit from this class — any object that
    exposes the attributes and methods below is a valid ``Source``.

    Example
    -------
    ::

        class GitHubSource:
            @property
            def name(self) -> str:
                return "kiro-configs"

            def fetch(self) -> FetchResult:
                # ... fetch files from GitHub ...
                return FetchResult(version=commit_sha, files=files)
    """

    @property
    def name(self) -> str:
        """Unique name identifying this source, matching the config entry."""
        ...

    def fetch(self) -> FetchResult:
        """Fetch the current desired state from the source.

        Returns a :class:`FetchResult` containing all files and the version
        identifier of the snapshot that was retrieved.

        Raises
        ------
        SourceFetchError
            If the source cannot be reached or authentication fails.
        """
        ...


class SourceFetchError(Exception):
    """Raised when a source fails to fetch desired state.

    Wraps the underlying exception so callers can handle fetch failures
    without depending on source-specific exception types.
    """
