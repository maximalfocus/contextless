# Security policy

## This project contains an intentional vulnerability

`contextless` is an educational demonstration. It **deliberately** ships a vulnerable application that
compiles user input as a template (Server-Side Template Injection — OWASP A03:2021, CWE-1336 / CWE-94).
This is the whole point of the project, not a defect.

**Please do not report the demonstrated SSTI behaviour as a vulnerability.** It is intended, documented
in the [walkthrough](docs/WALKTHROUGH.md), and confined to local use:

- the vulnerable app runs only behind two deliberate opt-in actions (its Compose profile **and**
  `ALLOW_VULNERABLE_DEMO=true`);
- its only executed command is the read-only `id`, inside a hardened container (non-root, all
  capabilities dropped, `no-new-privileges`, read-only root filesystem, no network egress);
- all organizations, users, orders, tokens, and "secrets" are fictional.

## Reporting an *unintended* vulnerability

If you find a security issue that is **not** the intentionally demonstrated SSTI — for example a flaw in
the secure app's data-into-context path, the restricted-render sandbox, the container hardening, or the
build/CI configuration — please report it **privately**:

- Use GitHub's **private vulnerability reporting** on this repository: the **Security** tab →
  **Report a vulnerability**. This opens a private advisory visible only to the maintainers.

Please do not open a public issue for an unintended vulnerability until it has been addressed.

## Scope and expectations

This is educational software provided under the [MIT License](LICENSE) with no warranty. There is no
service-level agreement, no guaranteed response time, and no production-support commitment. Nothing in
this repository is hosted or operated as a service.
