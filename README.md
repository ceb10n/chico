# chico

<p align="center">
  <img src="https://raw.githubusercontent.com/ceb10n/chico/master/docs/assets/logo.png" alt="chico logo" width="400"/>
</p>

<br/>


[![CI](https://github.com/ceb10n/chico/actions/workflows/publish.yml/badge.svg)](https://github.com/ceb10n/chico/actions)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/chico-ai)](https://pypi.org/project/chico-ai)
[![PyPI - License](https://img.shields.io/pypi/l/chico-ai)](https://pypi.org/project/chico-ai)

`chico` is an agent-native configuration control plane — a deterministic reconciliation engine for distributed configuration state, designed for both humans and agents.

📖 **[Full documentation](https://ceb10n.github.io/chico)**

## ✨ Why chico?

- Keep your AI agent configuration in a Git repository and sync it automatically
- Plan/apply lifecycle — preview every change before it happens
- Automatic scheduling via cron (macOS/Linux) or Task Scheduler (Windows)
- Structured JSON logging for full auditability
- Works with any GitHub repository, public or private

## ⚡ Quick Start

Initialize chico with a GitHub source in one command:

```bash
chico-ai init \
  --source github \
  --repo Chico-inc/agents-patterns \
  --path patterns \
  --source-prefix patterns/ \
  --target kiro \
  --branch master
```

Then sync:

```bash
chico-ai sync
```

That's it — chico fetches every file under `patterns/` from the repository and applies it to `~/.kiro/`.

## ✅ Features

- Sync configuration files from **GitHub repositories** to your local agent environment
- **Plan/apply lifecycle** — see exactly what will change before committing
- **`chico-ai sync`** — plan and apply in a single step
- **Automatic scheduling** — `chico-ai schedule install --every 30` sets up a recurring sync
- Recursive directory traversal — syncs nested folder structures automatically
- UTF-8 and Latin-1 encoding support for international content
- 100% test coverage

## 🔧 Requirements

| Python |
| :----- |
| 3.11+  |

## 💽 Installation

```bash
pip install chico-ai
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install chico-ai
```

Or run without installing:

```bash
uvx chico-ai --help
```

## 📦 Usage

### Initialize

```bash
chico-ai init \
  --source github \
  --repo Chico-inc/agents-patterns \
  --path patterns \
  --source-prefix patterns/ \
  --target kiro \
  --branch master
```

Creates `~/.chico/config.yaml` pre-populated and ready to use. For an empty config to edit manually:

```bash
chico-ai init
```

### Plan

Preview what would change without writing anything to disk:

```bash
chico-ai plan
chico-ai plan hooks          # plan a single source
```

### Apply

Apply the changes computed by plan:

```bash
chico-ai apply
chico-ai apply steering-files  # apply a single source
```

### Sync

Plan and apply in one step:

```bash
chico-ai sync
chico-ai sync my-config       # sync a single source
```

### Schedule

Install a recurring sync (every 30 minutes by default):

```bash
chico-ai schedule install
chico-ai schedule install --every 15
chico-ai schedule install --every 30 --source hooks   # schedule a single source
chico-ai schedule status
chico-ai schedule uninstall
```

### Environment variables

| Variable | Description |
| :------- | :---------- |
| `GITHUB_TOKEN` | GitHub personal access token for private repositories |

## ⚙️ Configuration

chico reads `~/.chico/config.yaml`:

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

| Field | Description |
| :---- | :---------- |
| `repo` | GitHub repository in `owner/repo` format |
| `path` | Directory inside the repo to sync |
| `source_prefix` | Prefix stripped from source paths when mapping to local files. Defaults to `path` |
| `branch` | Branch to read from |
| `target` | Provider name this source feeds into |

## Provider fields

| Field | Description |
| :---- | :---------- |
| `name` | Unique provider name |
| `type` | Provider type (`kiro`) |
| `level` | `global` for `~/.kiro/`, `project` for a specific target directory |
| `path` | Absolute path to the target directory (project level only). Files are synced directly into this path — no `.kiro/` is appended. Recorded automatically by `chico-ai init --level project` as `{cwd}/.kiro` |

## 👩🏼‍⚖️ License

This project is licensed under the terms of the [MIT license.](LICENSE)
