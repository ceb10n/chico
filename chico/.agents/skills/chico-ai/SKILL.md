---
name: chico-ai
description: chico-ai best practices and conventions. Use when setting up, configuring, or running chico-ai — an agent-native configuration control plane that syncs configuration files from GitHub repositories to the local agent environment (e.g. ~/.kiro/). Use when the user asks to set up chico, sync agent config, run chico plan or apply, configure a schedule, or troubleshoot chico errors.
---

# chico-ai

Official chico-ai skill to configure, run, and troubleshoot `chico-ai` following best practices.

## The CLI command is `chico-ai`

Always use `chico-ai` as the command, not `chico`.

```bash
chico-ai --help
chico-ai init
chico-ai sync
```

## Installation

```bash
# permanent install
uv tool install chico-ai

# run without installing
uvx chico-ai --help
```

## Initialize with flags, not manual editing

When the user knows their repo and path, use `chico-ai init` with flags to generate the config automatically.

```bash
chico-ai init \
  --source github \
  --repo my-org/my-configs \
  --path ai-config/ \
  --source-prefix ai-config/ \
  --branch main
```

instead of:

```bash
# DO NOT DO THIS (unless user explicitly wants to edit manually)
chico-ai init
# then manually editing ~/.chico/config.yaml
```

## Always set `source_prefix` equal to `path`

`source_prefix` is stripped from file paths when mapping from the repo to the local directory. If it doesn't match `path`, files will either not be found or be written to wrong locations.

Do this:

```yaml
sources:
  - name: my-configs
    type: github
    repo: my-org/my-configs
    branch: main
    path: ai-config/
    source_prefix: ai-config/
    target: kiro
```

instead of:

```yaml
# DO NOT DO THIS — source_prefix missing or mismatched
sources:
  - name: my-configs
    type: github
    repo: my-org/my-configs
    branch: main
    path: ai-config/
    target: kiro
```

If the user wants to sync only a subdirectory, both `path` and `source_prefix` should point to that subdirectory:

```yaml
path: ai-config/steering/
source_prefix: ai-config/steering/
```

## Use `chico-ai sync` for one-shot syncing

`chico-ai sync` runs plan and apply together. Prefer it when the user just wants to sync without reviewing changes first.

```bash
chico-ai sync
```

Use `chico-ai plan` then `chico-ai apply` separately when the user wants to review changes before applying:

```bash
chico-ai plan    # preview only, never writes to disk
chico-ai apply   # apply after reviewing
```

## Never edit `~/.chico/state.json` manually

`state.json` is managed exclusively by `chico-ai apply` and `chico-ai sync`. Manual edits will corrupt state and cause incorrect diffs on the next run.

## GitHub token for private repositories

```bash
export GITHUB_TOKEN=ghp_...
```

Public repositories do not need a token. Never hardcode the token in `config.yaml`.

## Scheduling automatic syncs

```bash
# install — default is every 30 minutes
chico-ai schedule install

# custom interval
chico-ai schedule install --every 15

chico-ai schedule status
chico-ai schedule uninstall
```

Intervals must be between 1 and 59 minutes on macOS/Linux (cron). On Windows the limit is 1–1439 minutes (Task Scheduler).

## Troubleshooting

### "message: not found" during sync

The `path` in `config.yaml` does not exist in the repository. Verify the exact directory path and branch name directly in GitHub.

### No changes detected despite new files in the repo

`source_prefix` does not match `path`. Set both to the same value.

### UTF-8 decode error

chico-ai falls back to Latin-1 automatically for files that cannot be decoded as UTF-8. If the error persists, the file likely uses an unsupported encoding.

### "No chico scheduled task found" on uninstall

The schedule was never installed, or it was removed manually from cron/Task Scheduler. Run `chico-ai schedule status` to confirm before uninstalling.
