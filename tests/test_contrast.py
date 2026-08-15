"""Side-by-side contrast between the vulnerable and secure apps (FR-007, FR-013)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from contextless.config import DEMO_SENTINEL, FICTIONAL_INTEGRATION_API_KEY
from tests.conftest import GLOBEX_TOKEN, auth

BENIGN = "Order {{ order.number }} for {{ order.customer_name }} has shipped"
EXPECTED_BENIGN = "Order 1001 for Alice Anderson has shipped"
RCE_PAYLOAD = "{{ cycler.__init__.__globals__.os.popen('id').read() }}"
LADDER = [
    "{{ 7*191 }}",
    "{{ config.integration_api_key }}",
    RCE_PAYLOAD,
]


def _render(client: TestClient, body: str) -> str:
    response = client.post(
        "/notifications/preview",
        headers=auth(GLOBEX_TOKEN),
        json={"body": body, "order_reference": "1001"},
    )
    assert response.status_code == 200, response.text
    rendered: str = response.json()["rendered"]
    return rendered


def test_benign_input_is_identical_across_apps(
    client: TestClient, vulnerable_client: TestClient
) -> None:
    secure = _render(client, BENIGN)
    vulnerable = _render(vulnerable_client, BENIGN)
    assert secure == vulnerable == EXPECTED_BENIGN


def test_secure_keeps_every_ladder_payload_inert(client: TestClient) -> None:
    for payload in LADDER:
        rendered = _render(client, payload)
        assert rendered == payload  # echoed verbatim
        assert "1337" not in rendered
        assert "uid=" not in rendered
        assert FICTIONAL_INTEGRATION_API_KEY not in rendered
        assert DEMO_SENTINEL not in rendered


def test_vulnerable_executes_every_ladder_payload(vulnerable_client: TestClient) -> None:
    assert _render(vulnerable_client, "{{ 7*191 }}") == "1337"
    secret = _render(vulnerable_client, "{{ config.integration_api_key }}")
    assert secret == FICTIONAL_INTEGRATION_API_KEY
    assert "uid=" in _render(vulnerable_client, RCE_PAYLOAD)


def test_secure_reveals_no_structural_error_oracle(client: TestClient) -> None:
    # Every injection returns a normal 200 with literal text — never a 500 or an
    # error disclosing engine, module, or attribute structure.
    for payload in LADDER:
        response = client.post(
            "/notifications/preview",
            headers=auth(GLOBEX_TOKEN),
            json={"body": payload, "order_reference": "1001"},
        )
        assert response.status_code == 200
        assert "Traceback" not in response.text
