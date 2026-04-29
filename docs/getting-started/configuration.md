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
| `level` | string | `global` for `~/.kiro/`, `project` for `.kiro/` |
