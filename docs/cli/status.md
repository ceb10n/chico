# chico-ai status

Show the current sync status, per-source details, and last applied state.

```bash
chico-ai status
```

## Example output

```
Status: idle

Last run: 2026-04-29T14:30:00+00:00
  Applied: 5
  Errors:  0

Sources (2):

  steering
    version:   abc123def456
    resources: 3 (3 ok, 0 error)

  hooks
    version:   def789abc012
    resources: 2 (2 ok, 0 error)

Total resources: 5 tracked
```

Each source shows its last synced commit SHA (truncated to 12 chars) and a breakdown of how many resources were applied from that source.
