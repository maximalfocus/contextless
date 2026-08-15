# Contributing to contextless

Thanks for your interest! `contextless` is a small, local, container-only educational demonstration of
Server-Side Template Injection. Contributions that make the lesson clearer, safer, or more correct are
welcome.

## Ground rules

- **The vulnerable app is intentional.** `src/contextless/apps/vulnerable.py` and its renderer are
  deliberately insecure local educational code. Please don't "fix" the SSTI — improve how the demo
  explains or contains it. See [`SECURITY.md`](SECURITY.md).
- **Keep everything fictional and local.** No real organizations, endpoints, credentials, or personal
  data. No hosted service, deployment, or published image is in scope.
- **The read-only boundary stays.** The only command the demonstration executes is `id`. Do not add
  destructive, persistent, filesystem-writing, stacked, or egress-producing behaviour.

## Development

Only **Docker** (with the Compose plugin) is required — no host Python or project packages.

```sh
# Lint, type-check, and test through the same boundary CI uses
docker compose run --build --rm verify

# Secure demo over HTTP
docker compose run --build --rm demo

# Full comparison of both apps (two opt-in actions)
ALLOW_VULNERABLE_DEMO=true docker compose --profile compare --profile vulnerable run --build --rm compare
```

Please make sure `docker compose run --build --rm verify` (Ruff, mypy, and pytest) is green before
opening a pull request, and add tests for behaviour changes.

## Expectations

This is educational software provided as-is under the [MIT License](LICENSE). There is no support
commitment or guaranteed response time, and no access to any private material is required to build,
test, or contribute.
