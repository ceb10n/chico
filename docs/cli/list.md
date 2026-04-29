# chico-ai list

Show all configured sources and providers.

```bash
chico-ai list
```

## Example output

```
Providers (2):

  kiro
    type:  kiro
    level: global

  kiro-local
    type:  kiro
    level: project
    path:  /home/user/my-project/.kiro

Sources (2):

  steering
    type:   github
    repo:   org/config
    path:   steering
    branch: main
    target: kiro
    prefix: steering/

  hooks
    type:   github
    repo:   org/hooks
    path:   hooks
    branch: develop
    target: kiro
```
