# Configuration

chico reads its configuration from `~/.chico/config.yaml`.

## Full example

```yaml
sources:
  - name: agents-patterns
    type: github
    repo: Chico-inc/agents-patterns
    branch: master
    path: patterns
    source_prefix: patterns/
    target: kiro

providers:
  - name: kiro
    type: kiro
    level: global
```

## Sources

You can configure multiple sources. Each is processed independently during
`plan`, `apply`, and `sync`. Pass a source name to any of those commands to
operate on a single source (e.g. `chico-ai plan agents-patterns`).

| Field | Type | Description |
|---|---|---|
| `name` | string | Unique name for this source. Used as the argument to filter commands |
| `type` | string | Source type (`github`) |
| `repo` | string | GitHub repository in `owner/repo` format |
| `branch` | string | Branch to sync from |
| `path` | string | Path inside the repo to sync |
| `source_prefix` | string | Prefix to strip when mapping to the local path. Defaults to `path` |
| `target` | string | Provider name this source feeds into |

## Providers

| Field | Type | Description |
|---|---|---|
| `name` | string | Unique name for this provider |
| `type` | string | Provider type (`kiro`) |
| `level` | string | `global` for `~/.kiro/`, `project` for a specific directory |
| `path` | string | Absolute path to the target directory. Only used when `level` is `project`. Files are synced directly into this path — no `.kiro/` is appended. Recorded automatically by `chico-ai init --level project` as `{cwd}/.kiro` |

## Project-level example

Sync specs from a GitHub repo into a project's `.kiro/` directory:

```yaml
sources:
  - name: my-specs
    type: github
    repo: my-org/my-repo
    branch: main
    path: .kiro/specs
    source_prefix: .kiro/
    target: kiro-local

providers:
  - name: kiro-local
    type: kiro
    level: project
    path: /home/user/my-project/.kiro
```

This syncs `.kiro/specs/design.md` from the repo to `/home/user/my-project/.kiro/specs/design.md`.

The `path` field is the exact target directory — chico does not append `.kiro/` to it. This avoids double-nesting when the source files already live under `.kiro/` in the repository.

## Multiple providers example

You can mix global and project-level providers:

```yaml
providers:
  - name: kiro
    type: kiro
    level: global

  - name: kiro-local
    type: kiro
    level: project
    path: /home/user/my-project/.kiro

sources:
  - name: steering
    type: github
    repo: my-org/config
    path: steering
    source_prefix: steering/
    target: kiro

  - name: project-specs
    type: github
    repo: my-org/config
    path: .kiro/specs
    source_prefix: .kiro/
    target: kiro-local
```
