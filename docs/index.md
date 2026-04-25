# chico

**chico** is an agent-native configuration control plane — a deterministic reconciliation engine for distributed configuration state, designed for both humans and agents.


## Features

- Sync configuration files from GitHub repositories to your local agent environment
- Plan/apply lifecycle — see what will change before it changes
- Automatic scheduling (cron on macOS/Linux, Task Scheduler on Windows)
- Structured JSON logging

## Install

```bash
pip install chico-ai
```

## Quick example

```bash
chico-ai init
chico-ai plan
chico-ai apply
```
