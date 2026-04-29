# chico-ai add

Add sources or providers to an existing configuration.

## add source

```bash
chico-ai add source --repo org/repo --path configs/
```

| Option | Default | Description |
|---|---|---|
| `--repo` | (required) | GitHub repository in `owner/repo` format |
| `--path` | (required) | Directory path inside the repository |
| `--type` | `github` | Source type |
| `--name` | repo name | Custom source name. Defaults to the repo name |
| `--branch` | `main` | Branch to read from |
| `--target` | `kiro` | Provider name to sync into |
| `--source-prefix` | same as `--path` | Prefix to strip from source paths |

### Examples

```bash
# Add a source targeting the default global provider
chico-ai add source --repo my-org/steering --path steering/

# Add with a custom name and branch
chico-ai add source --repo my-org/config --path .kiro/specs \
  --name project-specs --branch develop --target kiro-local \
  --source-prefix .kiro/
```

## add provider

```bash
chico-ai add provider --name kiro-local
```

| Option | Default | Description |
|---|---|---|
| `--name` | (required) | Unique provider name |
| `--type` | `kiro` | Provider type |
| `--level` | `global` | `global` for `~/.kiro/`, `project` for a specific directory |
| `--path` | `{cwd}/.kiro` | Target directory (project level only) |

### Examples

```bash
# Add a global provider
chico-ai add provider --name kiro-global

# Add a project-level provider for the current directory
chico-ai add provider --name kiro-local --level project

# Add a project-level provider with a custom path
chico-ai add provider --name kiro-local --level project \
  --path /home/user/my-project/.kiro
```
