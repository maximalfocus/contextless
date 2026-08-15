# contextless

A small, **local, container-only** educational demonstration of **Server-Side Template Injection
(SSTI)** — OWASP **A03:2021 Injection**, **CWE-1336** — and the fix that prevents it: keeping user
input as **data** in the render **context** of a fixed template instead of compiling it as template
**source**.

This project is educational code intended to run only on a developer's machine. It hosts nothing,
deploys nothing, and makes no production-readiness claim.

> **Status:** the secure baseline, the opt-in vulnerable contrast app, the SSTI escalation ladder, the
> comparison CLI, the regression matrix, and the [walkthrough](docs/WALKTHROUGH.md) are all in place.
> Repository publication is prepared in a subsequent change.

**New here? Start with the [walkthrough](docs/WALKTHROUGH.md).** It explains data-versus-template-source,
maps the terminology (SSTI · OWASP A03:2021 · CWE-1336 · CWE-94), and walks the whole demo in five
minutes.

## Requirements

Only **Docker** (with the Docker Compose plugin). No host Python, `uv`, or project packages are needed.

## Quick start

```sh
# Run the secure API on http://127.0.0.1:8000 (loopback only)
docker compose up --build secure

# One-shot secure demo over real localhost HTTP
docker compose run --build --rm demo

# Full side-by-side comparison of BOTH apps (two opt-in actions — see below)
ALLOW_VULNERABLE_DEMO=true docker compose --profile compare run --build --rm compare

# Verification boundary — ruff + mypy + pytest, identical locally and in CI
docker compose run --build --rm verify

# Dispose of all state
docker compose down -v
```

The image copies source in at build time, so pass `--build` after editing code. While a service is up,
its OpenAPI docs are at `/docs` (`http://127.0.0.1:8000/docs`, `http://127.0.0.1:8001/docs`).

## The vulnerable app (opt-in, local only)

> ⚠️ **The vulnerable application is intentionally insecure local educational code. Never deploy it.**

It compiles user input as a template, so it demonstrates the full SSTI escalation ladder — expression
evaluation, secret disclosure, and object-graph traversal reaching `os.popen('id')` for in-container
code execution. To contain it, starting it needs **two deliberate actions** — its opt-in Compose
profile **and** `ALLOW_VULNERABLE_DEMO=true` — and it runs non-root with all capabilities dropped,
`no-new-privileges`, a read-only root filesystem, and **no network egress**. The code-execution proof
is confined to the single read-only `id` command; destructive, persistent, and egress-producing
payloads are out of scope by design.

```sh
# Vulnerable app for manual exploration on 127.0.0.1:8001
ALLOW_VULNERABLE_DEMO=true docker compose --profile vulnerable up --build vulnerable vuln-proxy

# Prove the container hardening + no egress
ALLOW_VULNERABLE_DEMO=true bash scripts/verify-vulnerable-hardening.sh
```

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

## Two secure paths

**Primary control — data into context (`POST /notifications/preview`).** User input is never compiled
as a template. This is the fix you should reach for: keep user data in the render context of a fixed
template and no injection is possible.

**Defence-in-depth — restricted render (`POST /notifications/preview/restricted`).** For the case where
a product *genuinely must* let users author template logic, the secure app also offers a sandboxed
path (`jinja2.sandbox.SandboxedEnvironment`) with constrained attribute access, strict undefined
handling, and an **explicit allowlist of exposed names** (only `order`). An allowlisted body such as
`{% if order.status == 'shipped' %}…{% endif %}` renders; a disallowed construct — a non-exposed name
or an object-graph traversal — is rejected with a generic response that does not enumerate the
permitted names, and each rejection emits exactly one generic structured JSON audit event (with a
correlation id echoed to the client, no payload, no secret, no token).

> This restricted path is a **secondary mitigation, not the primary control.** Template-engine sandbox
> escapes are a recurring vulnerability class, so untrusted template authoring should be avoided
> wherever the data-into-context approach is sufficient.

## Safety

All organizations, users, customers, orders, tokens, and "secrets" in this repository are fictional.
The demonstration is non-destructive and performs no network egress beyond loopback.

## Contributing & security

Contributions are welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md). The intentionally vulnerable app
is deliberate; please read [`SECURITY.md`](SECURITY.md), which separates the demonstrated SSTI from
unintended vulnerabilities and gives a private reporting path for the latter.

This project is **not hosted or operated as a service** and makes **no production-readiness, support, or
compatibility promise**.

## License

Licensed under the [MIT License](LICENSE) — SPDX `MIT`.
