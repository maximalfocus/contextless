# contextless

A small, **local, container-only** educational demonstration of **Server-Side Template Injection
(SSTI)** — OWASP **A03:2021 Injection**, **CWE-1336** — and the fix that prevents it: keeping user
input as **data** in the render **context** of a fixed template instead of compiling it as template
**source**.

This project is educational code intended to run only on a developer's machine. It hosts nothing,
deploys nothing, and makes no production-readiness claim.

> **Status:** the secure baseline is in place. The opt-in vulnerable contrast app, the SSTI escalation
> ladder, the comparison CLI, the full regression matrix, and the complete walkthrough are being added
> in subsequent changes.

## Requirements

Only **Docker** (with the Docker Compose plugin). No host Python, `uv`, or project packages are needed.

## Quick start

```sh
# Run the secure API on http://127.0.0.1:8000 (loopback only)
docker compose up --build secure

# One-shot: seed fresh deterministic state, exercise the secure app over real
# localhost HTTP, print the outcome, and exit
docker compose run --build --rm demo

# Verification boundary — ruff + mypy + pytest, identical locally and in CI
docker compose run --build --rm verify

# Dispose of all state
docker compose down -v
```

The image copies source in at build time, so pass `--build` after editing code.

Interactive API docs are available at `http://127.0.0.1:8000/docs` while the secure service is up.

## What the secure app shows

`POST /notifications/preview` takes a notification `body` and an `order_reference` and returns the
rendered notification for the authenticated user's tenant. It **never compiles the body as a template**:
it substitutes only an allowlist of named placeholders (`order.number`, `order.customer_name`,
`order.status`) with the caller's own order data, and preserves everything else as inert literal text.

| Input body | Rendered output |
|---|---|
| `Order {{ order.number }} for {{ order.customer_name }} has shipped` | `Order 1001 for Alice Anderson has shipped` |
| `{{ 7*191 }}` | `{{ 7*191 }}` (literal — no evaluation) |
| `{{ config.integration_api_key }}` | `{{ config.integration_api_key }}` (literal — no secret) |
| `{{ ''.__class__.__mro__[1].__subclasses__() }}` | echoed verbatim (literal — no code execution) |

Authentication uses conspicuously fake, demo-only bearer tokens. Missing, malformed, and unknown
credentials all receive the same generic `401`.

## Safety

All organizations, users, customers, orders, tokens, and "secrets" in this repository are fictional.
The demonstration is non-destructive and performs no network egress beyond loopback.

## License

This project will be released under the **MIT License**; the `LICENSE` file is added as part of the
publication-preparation change.
