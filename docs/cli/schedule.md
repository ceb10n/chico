# chico-ai schedule

Manage the periodic sync schedule.

## Install

```bash
chico-ai schedule install
chico-ai schedule install --every 15
```

| Option | Default | Description |
|---|---|---|
| `--every` | `30` | Run interval in minutes |

Uses **cron** on macOS/Linux and **Windows Task Scheduler** on Windows.

## Uninstall

```bash
chico-ai schedule uninstall
```

## Status

```bash
chico-ai schedule status
```
