# chico-ai schedule

Manage the periodic sync schedule.

## Install

```bash
chico-ai schedule install
chico-ai schedule install --every 15
chico-ai schedule install --every 30 --source hooks
```

| Option | Default | Description |
|---|---|---|
| `--every` | `30` | Run interval in minutes |
| `--source` | — | Source name to sync. When omitted, all sources are synced |

Uses **cron** on macOS/Linux and **Windows Task Scheduler** on Windows.

## Uninstall

```bash
chico-ai schedule uninstall
```

## Status

```bash
chico-ai schedule status
```
