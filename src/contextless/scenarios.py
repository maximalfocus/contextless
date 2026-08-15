"""Scenario engine for the vulnerable/secure comparison.

Pure, transport-agnostic logic: given an HTTP client for an app, run the
escalation ladder and classify each result. This module contains no terminal I/O
and is directly testable by injecting an ``httpx.Client`` (including one bound to
an in-process ASGI app).
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from contextless.config import FICTIONAL_INTEGRATION_API_KEY

ORDER_REFERENCE = "1001"
RCE_PAYLOAD = "{{ cycler.__init__.__globals__.os.popen('id').read() }}"


@dataclass(frozen=True)
class Scenario:
    """One row of the escalation ladder."""

    key: str
    label: str
    body: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "benign",
        "benign order data",
        "Order {{ order.number }} for {{ order.customer_name }} has shipped",
    ),
    Scenario("expression", "expression evaluation", "{{ 7*191 }}"),
    Scenario("secret", "configuration / secret disclosure", "{{ config.integration_api_key }}"),
    Scenario("rce", "object-graph code execution", RCE_PAYLOAD),
)


@dataclass(frozen=True)
class Outcome:
    """The classified result of one scenario against one app."""

    scenario: Scenario
    status_code: int
    compiled_as: str
    rendered: str
    expression_evaluated: bool
    secret_leaked: bool
    code_executed: bool

    @property
    def verdict(self) -> str:
        dangerous = self.expression_evaluated or self.secret_leaked or self.code_executed
        return "VULNERABLE" if dangerous else "secure"


@dataclass(frozen=True)
class Comparison:
    """The secure and vulnerable outcomes for one scenario, side by side."""

    scenario: Scenario
    secure: Outcome
    vulnerable: Outcome


_COMPILED_AS = {"template-source": "template source", "data-into-context": "data"}


def classify(scenario: Scenario, status_code: int, rendered: str, render_mode: str) -> Outcome:
    """Derive the observable signals from a rendered response."""
    return Outcome(
        scenario=scenario,
        status_code=status_code,
        compiled_as=_COMPILED_AS.get(render_mode, render_mode or "unknown"),
        rendered=rendered,
        expression_evaluated="1337" in rendered,
        secret_leaked=FICTIONAL_INTEGRATION_API_KEY in rendered,
        code_executed="uid=" in rendered,
    )


def run_scenario(client: httpx.Client, token: str, scenario: Scenario) -> Outcome:
    """Send one scenario body to an app and classify the response."""
    response = client.post(
        "/notifications/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": scenario.body, "order_reference": ORDER_REFERENCE},
    )
    response.raise_for_status()
    data = response.json()
    return classify(scenario, response.status_code, data["rendered"], data["render_mode"])


def run_ladder(client: httpx.Client, token: str) -> list[Outcome]:
    """Run every scenario against a single app."""
    return [run_scenario(client, token, scenario) for scenario in SCENARIOS]


def compare(secure: httpx.Client, vulnerable: httpx.Client, token: str) -> list[Comparison]:
    """Run every scenario against both apps and pair the outcomes."""
    return [
        Comparison(
            scenario=scenario,
            secure=run_scenario(secure, token, scenario),
            vulnerable=run_scenario(vulnerable, token, scenario),
        )
        for scenario in SCENARIOS
    ]
