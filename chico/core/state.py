"""State management for chico.

The state file (``~/.chico/state.json``) is the source of truth for what
chico last applied. It tracks the commit hash (or equivalent version) of
every source that has been synced, enabling drift detection on subsequent
runs.

Example usage::

    from chico.core.state import State, load_state, save_state

    state = load_state()

    # After a successful apply from a GitHub source:
    state.record_version("kiro-configs", "abc123def456")
    save_state(state)

    # On the next run, check if the source has moved ahead:
    last_hash = state.get_version("kiro-configs")  # "abc123def456"
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from chico.core.paths import STATE_FILE


@dataclass
class State:
    """Represents the persisted state of chico.

    Attributes
    ----------
    status:
        High-level status of the last operation (``"idle"``, etc.).
    last_run:
        Metadata about the most recent run (result, change count, etc.).
        ``None`` if chico has never been applied.
    resources:
        List of resource snapshots recorded during the last apply.
    versions:
        Mapping of source name → version string (e.g. commit SHA) of the
        last successfully applied snapshot for that source.
    """

    status: str = "idle"
    last_run: dict | None = None
    resources: list[dict] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)

    def record_version(self, source_name: str, version: str) -> None:
        """Record the version of a source that was just applied.

        Parameters
        ----------
        source_name:
            The name of the source as declared in ``config.yaml``.
        version:
            The version identifier (e.g. full Git commit SHA) of the
            snapshot that was applied.
        """
        self.versions[source_name] = version

    def get_version(self, source_name: str) -> str | None:
        """Return the last applied version for a source, or ``None``.

        Parameters
        ----------
        source_name:
            The name of the source to look up.
        """
        return self.versions.get(source_name)


def load_state() -> State:
    """Load state from ``~/.chico/state.json``.

    Returns a default :class:`State` if the file does not exist yet
    (e.g. right after ``chico init``).
    """
    if not STATE_FILE.exists():
        return State()

    raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return State(
        status=raw.get("status", "idle"),
        last_run=raw.get("last_run"),
        resources=raw.get("resources", []),
        versions=raw.get("versions", {}),
    )


def save_state(state: State) -> None:
    """Persist a :class:`State` to ``~/.chico/state.json``.

    Creates the parent directory if it does not exist.

    Parameters
    ----------
    state:
        The state to write.
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(
            {
                "status": state.status,
                "last_run": state.last_run,
                "resources": state.resources,
                "versions": state.versions,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
