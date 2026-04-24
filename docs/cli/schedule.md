# chico schedule

Manage the periodic sync schedule.

## Install

```bash
chico schedule install
chico schedule install --every 15
```

| Option | Default | Description |
|---|---|---|
| `--every` | `30` | Run interval in minutes |

Uses **cron** on macOS/Linux and **Windows Task Scheduler** on Windows.

## Uninstall

```bash
chico schedule uninstall
```

## Status

```bash
chico schedule status
```
