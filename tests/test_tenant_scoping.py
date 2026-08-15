"""A caller only ever sees its own tenant's order data."""

from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from tests.conftest import GLOBEX_TOKEN, INITECH_TOKEN, auth


def _preview(client: TestClient, token: str, order_reference: str) -> httpx.Response:
    response: httpx.Response = client.post(
        "/notifications/preview",
        headers=auth(token),
        json={"body": "{{ order.number }}", "order_reference": order_reference},
    )
    return response


def test_globex_can_read_its_own_order(client: TestClient) -> None:
    response = _preview(client, GLOBEX_TOKEN, "1001")
    assert response.status_code == 200
    assert response.json()["rendered"] == "1001"
    assert response.json()["tenant"] == "globex"


def test_globex_cannot_read_initech_order(client: TestClient) -> None:
    # Order 2001 belongs to the initech tenant; globex must get a 404, not data.
    response = _preview(client, GLOBEX_TOKEN, "2001")
    assert response.status_code == 404


def test_initech_cannot_read_globex_order(client: TestClient) -> None:
    response = _preview(client, INITECH_TOKEN, "1001")
    assert response.status_code == 404


def test_initech_reads_its_own_order(client: TestClient) -> None:
    response = _preview(client, INITECH_TOKEN, "2001")
    assert response.status_code == 200
    assert response.json()["tenant"] == "initech"
