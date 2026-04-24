# Configuration

chico reads its configuration from `~/.chico/config.yaml`.

## Full example

```yaml
sources:
  - name: my-repo
    type: github
    repo: my-org/my-repo
    branch: main
    path: ai-config/
    source_prefix: ai-config/

providers:
  - name: kiro
    type: kiro
    target: my-repo
```

## Sources

| Field | Type | Description |
|---|---|---|
| `name` | string | Unique name for this source |
| `type` | string | Source type (`github`) |
| `repo` | string | GitHub repository in `owner/repo` format |
| `branch` | string | Branch to sync from |
| `path` | string | Path inside the repo to sync |
| `source_prefix` | string | Prefix to strip when mapping to the local path |

## Providers

| Field | Type | Description |
|---|---|---|
| `name` | string | Unique name for this provider |
| `type` | string | Provider type (`kiro`) |
| `target` | string | Name of the source to sync from |
