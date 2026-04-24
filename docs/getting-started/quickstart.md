# Quick Start

## 1. Initialize

```bash
chico init
```

This creates `~/.chico/config.yaml` with a sample configuration.

## 2. Edit the config

```yaml
sources:
  - name: my-repo
    type: github
    repo: my-org/my-repo
    branch: main
    path: config/
    source_prefix: config/

providers:
  - name: kiro
    type: kiro
    target: my-repo
```

## 3. Plan

```bash
chico plan
```

Preview what files will be synced.

## 4. Apply

```bash
chico apply
```

Download and apply the changes.

## 5. Sync (plan + apply in one step)

```bash
chico sync
```

## 6. Schedule automatic syncs

```bash
chico schedule install --every 30
```
