# chico-ai init

Set up chico-ai for the first time.

Creates `~/.chico/config.yaml` and `~/.chico/state.json`. Safe to run more than once — exits cleanly if already initialized.

## Usage

```bash
chico-ai init [OPTIONS]
```

## Options

| Option | Default | Description |
|---|---|---|
| `--source` | — | Source type to configure. Currently only `github` is supported. |
| `--repo` | — | GitHub repository in `owner/repo` format. Required when `--source` is set. |
| `--path` | — | Directory path inside the repository to fetch files from. Required when `--source` is set. |
| `--source-prefix` | same as `--path` | Prefix stripped from each file's path when mapping it to the local target. Defaults to `--path` if not set. |
| `--target` | `kiro` | Provider name to sync files into. |
| `--level` | `global` | Kiro level: `global` writes to `~/.kiro/`, `project` writes to `.kiro/` in a project directory. When `project` is used, the current working directory is recorded in the config so that scheduled syncs always write to the correct location. |
| `--branch` | `main` | Branch to read files from. |

## Examples

### Minimal — empty config to edit manually

```bash
chico-ai init
```

Creates `~/.chico/config.yaml` with empty providers and sources. Edit the file manually to add your repositories.

### Full — pre-populated and ready to use

```bash
chico-ai init \
  --source github \
  --repo Chico-inc/agents-patterns \
  --path patterns \
  --source-prefix patterns/ \
  --target kiro \
  --branch master
```

This writes a ready-to-use `~/.chico/config.yaml`. No manual editing needed — just run `chico-ai sync` next.

## Understanding `--path` vs `--source-prefix`

Given a repository with this structure:

```
patterns/
  steering/
    product.md
  rules/
    coding.md
```

- **`--path patterns`** — tells chico-ai to only look inside the `patterns/` directory.
- **`--source-prefix patterns/`** — strips `patterns/` from each file path when writing locally, so `patterns/steering/product.md` becomes `steering/product.md` inside `~/.kiro/`.

If you omit `--source-prefix`, it defaults to the value of `--path`, which is almost always what you want.

## What gets created

```
~/.chico/
  config.yaml   # your configuration
  state.json    # sync state (managed automatically)
```

## Next steps

After initializing, run:

```bash
chico-ai plan    # preview what will change
chico-ai apply   # apply the changes
# or
chico-ai sync    # plan + apply in one step
```
