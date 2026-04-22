"""Kiro provider for chico.

Maps files fetched from a source (GitHub, S3) to their local counterparts
inside a Kiro configuration directory and applies changes by writing files
to disk.

Kiro uses the same directory structure at both project and global level:

* Project-level: ``.kiro/`` at the workspace root
* Global-level:  ``~/.kiro/`` in the home directory

Steering files live under ``{kiro_dir}/steering/*.md``, and agent
definitions are declared in ``{kiro_dir}/steering/AGENTS.md``.

Example usage::

    from pathlib import Path
    from chico.providers.kiro import KiroProvider
    from chico.core.source import FetchResult

    fetch_result = github_source.fetch()

    # Project-level sync
    provider = KiroProvider(
        fetch_result=fetch_result,
        kiro_dir=Path(".kiro"),
        source_prefix="configs/",   # strip the repo prefix before mapping
    )

    for resource in provider.list_resources():
        diff = resource.diff()
        if diff.has_changes:
            resource.apply()
"""

from __future__ import annotations

import logging
from pathlib import Path

from chico.core.resource import (
    ChangeType,
    Diff,
    FieldChange,
    Resource,
    Result,
    ResultStatus,
)
from chico.core.source import FetchResult

logger = logging.getLogger("chico")


class KiroFileResource:
    """A single Kiro configuration file managed by chico.

    Represents one file from a source (e.g. ``steering/product.md``) mapped
    to its local path inside a Kiro directory. Knows how to diff and apply
    changes without affecting any other files.

    Parameters
    ----------
    source_path:
        The file's path as it appears in the source (e.g. ``steering/product.md``).
    source_content:
        The full text content fetched from the source.
    local_path:
        The absolute local path where the file should be written.
    """

    def __init__(self, source_path: str, source_content: str, local_path: Path) -> None:
        self._source_path = source_path
        self._source_content = source_content
        self._local_path = local_path

    @property
    def resource_id(self) -> str:
        """The absolute local path of this file, used as a stable identifier."""
        return str(self._local_path)

    def desired_state(self) -> dict:
        """Return the desired state as fetched from the source."""
        return {"content": self._source_content}

    def current_state(self) -> dict:
        """Return the current on-disk state, or ``{}`` if the file does not exist."""
        if not self._local_path.exists():
            return {}
        return {"content": self._local_path.read_text(encoding="utf-8")}

    def diff(self) -> Diff:
        """Compute the diff between desired and current state.

        Returns
        -------
        Diff
            * ``ChangeType.ADD`` — file does not exist locally yet.
            * ``ChangeType.MODIFY`` — file exists but content differs.
            * ``ChangeType.NONE`` — file exists and content matches.
        """
        current = self.current_state()

        if not current:
            return Diff(change_type=ChangeType.ADD, resource_id=self.resource_id)

        if self._source_content == current["content"]:
            return Diff(change_type=ChangeType.NONE, resource_id=self.resource_id)

        return Diff(
            change_type=ChangeType.MODIFY,
            resource_id=self.resource_id,
            changes={
                "content": FieldChange(
                    from_value=current["content"],
                    to_value=self._source_content,
                )
            },
        )

    def apply(self) -> Result:
        """Write the desired content to the local path.

        Creates any missing parent directories. Safe to call when the file
        is already in sync — the content is simply rewritten (idempotent).

        Returns
        -------
        Result
            ``ResultStatus.OK`` on success, ``ResultStatus.ERROR`` with a
            message if the write fails (e.g. permission denied).
        """
        try:
            self._local_path.parent.mkdir(parents=True, exist_ok=True)
            self._local_path.write_text(self._source_content, encoding="utf-8")
            return Result(status=ResultStatus.OK, resource_id=self.resource_id)
        except Exception as exc:
            return Result(
                status=ResultStatus.ERROR,
                resource_id=self.resource_id,
                message=str(exc),
            )


class KiroProvider:
    """Provider that maps source files to a local Kiro directory.

    Takes a :class:`~chico.core.source.FetchResult` and produces one
    :class:`KiroFileResource` per file, mapping source paths into the
    local ``kiro_dir``.

    Parameters
    ----------
    fetch_result:
        The result of calling ``source.fetch()``, containing the files
        and commit version to sync.
    kiro_dir:
        Root Kiro directory to sync into. Use ``.kiro/`` for project-level
        sync or ``Path.home() / ".kiro"`` for global sync.
    source_prefix:
        Optional prefix to strip from source paths before mapping to local
        paths. For example, if the GitHub repo stores files under
        ``configs/steering/``, set ``source_prefix="configs/"`` so the file
        lands at ``{kiro_dir}/steering/`` locally.

    Example
    -------
    ::

        provider = KiroProvider(
            fetch_result=github_source.fetch(),
            kiro_dir=Path(".kiro"),
            source_prefix="configs/",
        )
        for resource in provider.list_resources():
            print(resource.resource_id, resource.diff().change_type)
    """

    def __init__(
        self,
        fetch_result: FetchResult,
        kiro_dir: Path,
        source_prefix: str = "",
    ) -> None:
        self._fetch_result = fetch_result
        self._kiro_dir = kiro_dir
        self._source_prefix = source_prefix

    @property
    def name(self) -> str:
        """Provider name — always ``"kiro"``."""
        return "kiro"

    def list_resources(self) -> list[Resource]:
        """Return one :class:`KiroFileResource` per file in the fetch result.

        Source paths are mapped to local paths by:
        1. Stripping ``source_prefix`` from the beginning of the path.
        2. Joining the remainder onto ``kiro_dir``.

        For example, with ``source_prefix="configs/"`` and
        ``kiro_dir=Path(".kiro")``, the source path
        ``configs/steering/product.md`` maps to ``.kiro/steering/product.md``.
        """
        resources: list[Resource] = []
        for source_path, content in self._fetch_result.files.items():
            relative = source_path.removeprefix(self._source_prefix)
            local_path = self._kiro_dir / relative
            logger.info(
                "kiro.mapping",
                extra={
                    "source_path": source_path,
                    "local_path": str(local_path),
                    "prefix_stripped": self._source_prefix,
                },
            )
            resources.append(
                KiroFileResource(
                    source_path=source_path,
                    source_content=content,
                    local_path=local_path,
                )
            )
        return resources
