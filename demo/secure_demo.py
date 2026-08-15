"""One-shot secure-app demonstration over real localhost HTTP.

Authenticates as a fictional tenant user and previews several bodies against the
secure ``POST /notifications/preview`` endpoint: a benign body renders the
tenant's own order data, while an expression, a configuration-reading payload,
and an object-graph payload all render as inert literal text. Exits non-zero if
any expected outcome does not hold, so the container run doubles as a check.
"""

from __future__ import annotations

import os
import sys

import httpx

from contextless.config import FICTIONAL_INTEGRATION_API_KEY
from contextless.domain.fixtures import GLOBEX_TOKEN

BASE_URL = os.environ.get("CONTEXTLESS_BASE_URL", "http://127.0.0.1:8000")
ORDER_REFERENCE = "1001"

BENIGN_BODY = "Order {{ order.number }} for {{ order.customer_name }} has shipped"
EXPECTED_BENIGN = "Order 1001 for Alice Anderson has shipped"

PAYLOADS: list[tuple[str, str]] = [
    ("benign (allowlisted placeholders)", BENIGN_BODY),
    ("expression evaluation attempt", "{{ 7*191 }}"),
    ("configuration-read attempt", "{{ config.integration_api_key }}"),
    ("object-graph traversal attempt", "{{ ''.__class__.__mro__[1].__subclasses__() }}"),
]


def _preview(client: httpx.Client, token: str, body: str) -> httpx.Response:
    return client.post(
        "/notifications/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": body, "order_reference": ORDER_REFERENCE},
    )


def _restricted(client: httpx.Client, token: str, body: str) -> httpx.Response:
    return client.post(
        "/notifications/preview/restricted",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": body, "order_reference": ORDER_REFERENCE},
    )


def main() -> int:
    failures: list[str] = []

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        print(f"contextless secure demo → {BASE_URL}\n")
        print(f"{'scenario':<36} | {'rendered output'}")
        print("-" * 90)

        for label, body in PAYLOADS:
            response = _preview(client, GLOBEX_TOKEN, body)
            response.raise_for_status()
            rendered = response.json()["rendered"]
            print(f"{label:<36} | {rendered}")

            if label.startswith("benign"):
                if rendered != EXPECTED_BENIGN:
                    failures.append(
                        f"benign body rendered {rendered!r}, expected {EXPECTED_BENIGN!r}"
                    )
            elif rendered != body:
                failures.append(f"{label}: expected inert literal {body!r}, got {rendered!r}")
            if "1337" in rendered:
                failures.append(f"{label}: expression was evaluated (found 1337)")
            if FICTIONAL_INTEGRATION_API_KEY in rendered:
                failures.append(f"{label}: integration secret leaked")
            if "uid=" in rendered:
                failures.append(f"{label}: command execution reached (found uid=)")

        # Defence-in-depth restricted-render path: sandbox + explicit name allowlist.
        print("\nrestricted-render path (defence-in-depth: sandbox + name allowlist)")
        print("-" * 90)
        allowed = _restricted(client, GLOBEX_TOKEN, "{{ order.number }} / {{ order.status }}")
        allowed.raise_for_status()
        print(f"{'allowlisted body':<36} | {allowed.json()['rendered']}")
        if allowed.json()["rendered"] != "1001 / shipped":
            failures.append("restricted allowlisted body did not render as expected")

        rejected = _restricted(client, GLOBEX_TOKEN, "{{ config.integration_api_key }}")
        correlation = rejected.headers.get("X-Correlation-ID", "")
        print(
            f"{'disallowed construct':<36} | HTTP {rejected.status_code} "
            f"(rejected, correlation {correlation[:8]}…)"
        )
        if rejected.status_code != 400:
            failures.append(
                f"restricted disallowed construct returned {rejected.status_code}, want 400"
            )
        if FICTIONAL_INTEGRATION_API_KEY in rejected.text:
            failures.append("restricted rejection leaked the integration secret")
        if not correlation:
            failures.append("restricted rejection missing correlation id")

        # Authentication is generic: an unknown token is a plain 401.
        bad = _preview(client, "not-a-real-token", BENIGN_BODY)
        print(f"\n{'unknown token':<36} | HTTP {bad.status_code}")
        if bad.status_code != 401:
            failures.append(f"unknown token returned {bad.status_code}, expected 401")

    print()
    if failures:
        print("DEMO RESULT: FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("DEMO RESULT: PASS — secure app rendered data safely and kept injections inert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
