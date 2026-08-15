"""No request path mutates domain state; fixtures are stable across a run."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from contextless.domain.models import Order
from tests.conftest import GLOBEX_TOKEN, auth


def _order_snapshot(client: TestClient) -> list[tuple[int, str, str, int]]:
    engine = client.app.state.engine  # type: ignore[attr-defined]
    with Session(engine) as session:
        orders = session.scalars(select(Order).order_by(Order.id)).all()
        return [(o.id, o.number, o.status, o.tenant_id) for o in orders]


def test_state_is_unchanged_after_many_previews(client: TestClient) -> None:
    before = _order_snapshot(client)

    bodies = [
        "Order {{ order.number }} for {{ order.customer_name }} has shipped",
        "{{ 7*191 }}",
        "{{ config.integration_api_key }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    ]
    for body in bodies:
        client.post(
            "/notifications/preview",
            headers=auth(GLOBEX_TOKEN),
            json={"body": body, "order_reference": "1001"},
        )

    after = _order_snapshot(client)
    assert before == after


def test_two_fresh_apps_seed_identically() -> None:
    from contextless.apps.secure import create_secure_app

    first = create_secure_app()
    second = create_secure_app()
    with TestClient(first) as c1, TestClient(second) as c2:
        assert _order_snapshot(c1) == _order_snapshot(c2)
