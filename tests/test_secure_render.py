"""The secure endpoint renders data and keeps every injection inert."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contextless.config import DEMO_SENTINEL, FICTIONAL_INTEGRATION_API_KEY
from tests.conftest import GLOBEX_TOKEN, auth


def _render(client: TestClient, body: str, order_reference: str = "1001") -> dict[str, str]:
    response = client.post(
        "/notifications/preview",
        headers=auth(GLOBEX_TOKEN),
        json={"body": body, "order_reference": order_reference},
    )
    assert response.status_code == 200, response.text
    data: dict[str, str] = response.json()
    return data


def test_benign_body_renders_tenant_order_data(client: TestClient) -> None:
    result = _render(client, "Order {{ order.number }} for {{ order.customer_name }} has shipped")
    assert result["rendered"] == "Order 1001 for Alice Anderson has shipped"
    assert result["tenant"] == "globex"
    assert result["render_mode"] == "data-into-context"


def test_all_allowlisted_placeholders_resolve(client: TestClient) -> None:
    result = _render(client, "{{ order.number }}/{{ order.customer_name }}/{{ order.status }}")
    assert result["rendered"] == "1001/Alice Anderson/shipped"


@pytest.mark.parametrize(
    "payload",
    [
        "{{ 7*191 }}",
        "{{ config.integration_api_key }}",
        "{{ settings.SECRET_KEY }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ cycler.__init__.__globals__.os.popen('id').read() }}",
        "{% for x in range(3) %}{{ x }}{% endfor %}",
    ],
)
def test_injections_render_as_inert_literal_text(client: TestClient, payload: str) -> None:
    result = _render(client, payload)
    # The payload is echoed back verbatim: nothing is evaluated or substituted.
    assert result["rendered"] == payload
    assert "1337" not in result["rendered"]
    assert "uid=" not in result["rendered"]
    assert FICTIONAL_INTEGRATION_API_KEY not in result["rendered"]
    assert DEMO_SENTINEL not in result["rendered"]


def test_non_allowlisted_attribute_is_not_resolved(client: TestClient) -> None:
    # A near-miss on an allowlisted name must not resolve.
    result = _render(client, "{{ order.customer.name }} {{ order.tenant_id }}")
    assert result["rendered"] == "{{ order.customer.name }} {{ order.tenant_id }}"


def test_mixed_body_substitutes_only_allowlisted(client: TestClient) -> None:
    result = _render(client, "Hi {{ order.customer_name }} — {{ 7*191 }} — {{ order.status }}")
    assert result["rendered"] == "Hi Alice Anderson — {{ 7*191 }} — shipped"


def test_unknown_order_is_404(client: TestClient) -> None:
    response = client.post(
        "/notifications/preview",
        headers=auth(GLOBEX_TOKEN),
        json={"body": "x", "order_reference": "does-not-exist"},
    )
    assert response.status_code == 404
