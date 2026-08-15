# contextless — SSTI walkthrough

A five-minute, side-by-side tour of **Server-Side Template Injection (SSTI)** and the fix that
prevents it. Everything here runs locally in containers against fictional data.

> ⚠️ **The vulnerable application is intentionally insecure local educational code. Never deploy it.**
> Its code-execution proof is confined to the single read-only `id` command inside a hardened
> container with no network egress. Destructive, persistent, filesystem-writing, stacked, and
> egress-producing payloads are **out of scope by design**.

## Data versus template source — the whole idea

A template engine has two very different inputs:

- **template source** — the program text that the engine *compiles and executes* (`{{ ... }}`,
  `{% ... %}`); and
- **data** — the values placed into the render *context* that the template reads.

SSTI happens when **user input crosses from data into source**: the server takes text a user typed and
compiles it *as a template*. Now the user's input is code the server runs.

The two applications differ in exactly this:

| | secure (`POST /notifications/preview`) | vulnerable (`POST /notifications/preview`) |
|---|---|---|
| user body is treated as | **data** | **template source** |
| how it renders | fixed substitution of an allowlist of named placeholders | `Environment().from_string(body).render(...)` |
| `{{ 7*191 }}` | literal `{{ 7*191 }}` | `1337` |

## Terminology

- **SSTI** — Server-Side Template Injection.
- **OWASP** — **A03:2021 – Injection**.
- **CWE-1336** — *Improper Neutralization of Special Elements Used in a Template Engine*.
- **CWE-94** — *Improper Control of Generation of Code ('Code Injection')*.

In plain language: *user input crossing the boundary from data into the template that is compiled and
executed on the server.*

## The escalation ladder (vulnerable app)

Authenticated as a fictional tenant user, against fresh state:

1. **Baseline / legitimate.** `Order {{ order.number }} for {{ order.customer_name }} has shipped`
   → `Order 1001 for Alice Anderson has shipped`. Indistinguishable from ordinary use — and the secure
   app renders this **identically**.
2. **Expression evaluation.** `{{ 7*191 }}` → `1337`. The body is *evaluated*, not interpolated.
3. **Configuration / secret disclosure.** `{{ config.integration_api_key }}` →
   `sk-demo-INTEGRATION-0000-NOT-A-REAL-SECRET`. Data the endpoint never queries becomes visible.
4. **Object-graph traversal → in-container code execution.**
   `{{ cycler.__init__.__globals__.os.popen('id').read() }}` → a `uid=… gid=…` line, and the planted
   `DEMO_SENTINEL` is reachable in the render namespace. This proves arbitrary command execution inside
   the container — deliberately confined here to the read-only `id`.

Against the **secure** app, every one of these renders as **inert literal text**: no evaluation, no
secret, the `os` module unreachable, no command, and no error that reveals engine or module structure.

## Two lessons

1. **Primary control — keep user data in the render context.** Never compile untrusted input as a
   template. Render a fixed, developer-authored template and pass user data in as *data*. Blocklisting
   characters or keywords and "just escaping the output" are **not** defences.
2. **Defence-in-depth — a restricted engine with a name allowlist is *escapable* mitigation, not the
   primary control.** For products that genuinely must let users author template logic, the secure app
   also offers `POST /notifications/preview/restricted` using a sandboxed engine
   (`jinja2.sandbox.SandboxedEnvironment`) with an explicit allowlist of exposed names. A disallowed
   construct is rejected generically and emits one structured audit event. Treat this as secondary:
   **template-engine sandbox escapes are a recurring vulnerability class**, so avoid untrusted template
   authoring wherever the data-into-context approach suffices.

## Run it

Only Docker (with the Compose plugin) is required.

```sh
# Secure app only, on 127.0.0.1:8000
docker compose up --build secure

# Full side-by-side comparison of BOTH apps over real localhost HTTP
ALLOW_VULNERABLE_DEMO=true docker compose --profile compare run --build --rm compare

# The vulnerable app for manual exploration on 127.0.0.1:8001 (two opt-in actions)
ALLOW_VULNERABLE_DEMO=true docker compose --profile vulnerable up --build vulnerable vuln-proxy

# Verification: ruff + mypy + pytest (identical locally and in CI)
docker compose run --build --rm verify

# Prove the vulnerable container's hardening + no egress
ALLOW_VULNERABLE_DEMO=true bash scripts/verify-vulnerable-hardening.sh

# Dispose of all state
docker compose down -v
```

### Local OpenAPI exploration

While a service is up, its generated OpenAPI docs are served locally:

- secure: `http://127.0.0.1:8000/docs`
- vulnerable: `http://127.0.0.1:8001/docs`

### Expected `compare` output

For each payload the CLI prints, per app: whether the body was compiled as **template source** or
rendered as **data**, the rendered output, whether an **expression evaluated**, whether the
**integration secret leaked**, whether **`os.popen('id')` executed**, and an explicit
**vulnerable/secure verdict**. The vulnerable app is flagged on the three attack payloads; the secure
app is flagged on none; both produce identical benign output.

## Safety recap

- Only the read-only `id` is ever executed; the demo performs no destructive, persistent, or
  egress-producing action.
- Disposable fixture state is byte-for-byte identical before and after every run.
- The vulnerable container runs non-root, with all capabilities dropped, `no-new-privileges`, a
  read-only root filesystem, and **no network egress**.
- All organizations, users, customers, orders, tokens, and "secrets" are fictional.
