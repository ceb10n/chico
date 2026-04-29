# chico-ai sync

Plan and apply in a single step.

```bash
chico-ai sync
```

Equivalent to running `chico-ai plan` followed by `chico-ai apply`.

## Source filtering

Pass a source name to sync only that source:

```bash
chico-ai sync hooks
chico-ai sync steering-files
```

When omitted, all configured sources are synced.
