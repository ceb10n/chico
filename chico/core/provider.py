"""Provider protocol for chico.

A provider encapsulates a target system — such as a filesystem directory,
Kiro, or any future integration — and exposes the resources that system
contains as a flat list of :class:`~chico.core.resource.Resource` objects.

The plan engine calls :meth:`Provider.list_resources` to discover what
currently exists in a system before computing diffs.

Example usage::

    from chico.core.provider import Provider
    from chico.core.resource import Resource

    class FilesystemProvider:
        def __init__(self, root: Path) -> None:
            self._root = root

        @property
        def name(self) -> str:
            return f"filesystem:{self._root}"

        def list_resources(self) -> list[Resource]:
            return [
                ConfigFileResource(path)
                for path in self._root.glob("**/*.yaml")
            ]
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from chico.core.resource import Resource


@runtime_checkable
class Provider(Protocol):
    """Protocol that every chico provider must satisfy.

    A provider is responsible for a single target system. It knows how to
    enumerate all :class:`~chico.core.resource.Resource` objects that belong
    to that system, which the plan engine uses to compute the full changeset.

    Implementors do not need to inherit from this class — any object that
    exposes the attributes and methods below is a valid ``Provider``.

    Example
    -------
    ::

        class KiroProvider:
            @property
            def name(self) -> str:
                return "kiro"

            def list_resources(self) -> list[Resource]:
                return [KiroPromptResource(p) for p in kiro.list_prompts()]
    """

    @property
    def name(self) -> str:
        """Unique name identifying this provider (e.g. ``"filesystem"``, ``"kiro"``)."""
        ...

    def list_resources(self) -> list[Resource]:
        """Return all resources managed by this provider.

        The returned list reflects the *current* state of the system.
        Each resource is responsible for computing its own desired state
        and diff when requested by the plan engine.
        """
        ...
