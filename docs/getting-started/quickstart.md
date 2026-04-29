# Quick Start

## 1. Initialize

Pass all options to pre-populate the config in one step:

```bash
chico-ai init \
  --source github \
  --repo Chico-inc/agents-patterns \
  --path patterns \
  --source-prefix patterns/ \
  --target kiro \
  --branch master
```

This creates `~/.chico/config.yaml` ready to use. No manual editing needed.

## 2. Plan

```bash
chico-ai plan
```

Preview what files will be synced without writing anything to disk.

You can also scope to a single source:

```bash
chico-ai plan agents-patterns
```

## 3. Apply

```bash
chico-ai apply
```

Download and apply the changes.

## 4. Sync (plan + apply in one step)

```bash
chico-ai sync
```

All three commands accept an optional source name to operate on a single source.

## 5. Schedule automatic syncs

```bash
chico-ai schedule install --every 30
chico-ai schedule install --every 15 --source agents-patterns
```
