"""Core resource abstractions for chico.

This module defines the fundamental building blocks of chico's reconciliation
model. Every system that chico manages is represented as a :class:`Resource`.
Changes between desired and current state are described as a :class:`Diff`,
and the outcome of applying a change is captured in a :class:`Result`.

Example usage::

    from chico.core.resource import Resource, Diff, Result, ChangeType, ResultStatus

    class MyResource:
        @property
        def resource_id(self) -> str:
            return "my-resource"

        def desired_state(self) -> dict:
            return {"enabled": True}

        def current_state(self) -> dict:
            return {"enabled": False}

        def diff(self) -> Diff:
            return Diff(
                change_type=ChangeType.MODIFY,
                resource_id=self.resource_id,
                changes={"enabled": FieldChange(from_value=False, to_value=True)},
            )

        def apply(self) -> Result:
            # ... apply logic ...
            return Result(status=ResultStatus.OK, resource_id=self.resource_id)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class ChangeType(StrEnum):
    """Describes the nature of a change to a resource.

    Values
    ------
    ADD:
        The resource does not exist in the current state and will be created.
    MODIFY:
        The resource exists but one or more fields differ from the desired state.
    REMOVE:
        The resource exists in the current state but is absent from the desired state.
    NONE:
        The resource is fully in sync — no action required.
    """

    ADD = "add"
    MODIFY = "modify"
    REMOVE = "remove"
    NONE = "none"


@dataclass
class FieldChange:
    """Captures a before/after value for a single field within a :class:`Diff`.

    Attributes
    ----------
    from_value:
        The field's value in the current (live) state.
    to_value:
        The field's value in the desired state.
    """

    from_value: Any
    to_value: Any


@dataclass
class Diff:
    """Describes all changes required to bring a resource to its desired state.

    A ``Diff`` is the output of :meth:`Resource.diff`. It tells the plan engine
    *what* would change and *how*, without actually applying anything.

    Attributes
    ----------
    change_type:
        The high-level category of change (add, modify, remove, or none).
    resource_id:
        The unique identifier of the resource this diff belongs to.
    changes:
        A mapping of field names to their :class:`FieldChange`. Only populated
        when ``change_type`` is :attr:`ChangeType.MODIFY`.

    Properties
    ----------
    has_changes:
        ``True`` when there is at least one actionable change.
    """

    change_type: ChangeType
    resource_id: str
    changes: dict[str, FieldChange] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """Return ``True`` if this diff represents an actionable change."""
        return self.change_type != ChangeType.NONE


class ResultStatus(StrEnum):
    """Outcome of applying a resource change.

    Values
    ------
    OK:
        The change was applied successfully.
    ERROR:
        The change failed. Inspect :attr:`Result.message` for details.
    SKIPPED:
        The change was intentionally not applied (e.g. dry-run mode).
    """

    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class Result:
    """The outcome of calling :meth:`Resource.apply`.

    Attributes
    ----------
    status:
        Whether the apply succeeded, failed, or was skipped.
    resource_id:
        The unique identifier of the resource that was acted on.
    message:
        Optional human-readable detail, especially useful on error.
    """

    status: ResultStatus
    resource_id: str
    message: str = ""

    @property
    def ok(self) -> bool:
        """Return ``True`` when the result status is :attr:`ResultStatus.OK`."""
        return self.status == ResultStatus.OK


@runtime_checkable
class Resource(Protocol):
    """Protocol that every chico-managed resource must satisfy.

    A resource is the fundamental unit of chico's reconciliation model. It
    knows its own desired state (what it *should* look like) and current state
    (what it *actually* looks like), can compute the diff between the two, and
    can apply that diff.

    Implementors do not need to inherit from this class — any object that
    exposes the attributes and methods below is a valid ``Resource``.

    Example
    -------
    Implement the protocol on any plain class::

        class ConfigFileResource:
            def __init__(self, path: Path, desired: dict) -> None:
                self._path = path
                self._desired = desired

            @property
            def resource_id(self) -> str:
                return str(self._path)

            def desired_state(self) -> dict:
                return self._desired

            def current_state(self) -> dict:
                if self._path.exists():
                    return yaml.safe_load(self._path.read_text())
                return {}

            def diff(self) -> Diff:
                ...

            def apply(self) -> Result:
                ...
    """

    @property
    def resource_id(self) -> str:
        """Unique, stable identifier for this resource within its provider."""
        ...

    def desired_state(self) -> dict[str, Any]:
        """Return the full desired state for this resource as a plain dict."""
        ...

    def current_state(self) -> dict[str, Any]:
        """Return the current live state of this resource as a plain dict."""
        ...

    def diff(self) -> Diff:
        """Compute the diff between desired and current state.

        Returns a :class:`Diff` with ``change_type=ChangeType.NONE`` when
        the resource is already in sync.
        """
        ...

    def apply(self) -> Result:
        """Apply the changes described by :meth:`diff` to the live system.

        This method must be idempotent: calling it when the resource is
        already in sync must return :attr:`ResultStatus.OK` without side
        effects.
        """
        ...
