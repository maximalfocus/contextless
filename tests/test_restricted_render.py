"""The defence-in-depth restricted-render path: sandbox + name allowlist + audit."""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest
from fastapi.testclient import TestClient

from contextless.config import DEMO_SENTINEL, FICTIONAL_INTEGRATION_API_KEY
from contextless.logging_setup import AUDIT_LOGGER_NAME, JsonFormatter
from tests.conftest import GLOBEX_TOKEN, auth

RESTRICTED = "/notifications/preview/restricted"
GENERIC_DETAIL = "The notification template could not be rendered."


def _post(client: TestClient, body: str, order_reference: str = "1001") -> httpx.Response:
    response: httpx.Response = client.post(
        RESTRICTED,
        headers=auth(GLOBEX_TOKEN),
        json={"body": body, "order_reference": order_reference},
    )
    return response


@contextmanager
def _capture_audit() -> Iterator[io.StringIO]:
    """Capture audit-logger output emitted while the block runs."""
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(JsonFormatter())
    audit = logging.getLogger(AUDIT_LOGGER_NAME)
    audit.addHandler(handler)
    try:
        yield buffer
    finally:
        audit.removeHandler(handler)


def _audit_lines(buffer: io.StringIO) -> list[dict[str, str]]:
    return [json.loads(line) for line in buffer.getvalue().splitlines() if line.strip()]


def test_allowlisted_body_renders(client: TestClient) -> None:
    response = _post(client, "Order {{ order.number }} for {{ order.customer_name }}")
    assert response.status_code == 200, response.text
    assert response.json()["rendered"] == "Order 1001 for Alice Anderson"
    assert response.json()["render_mode"] == "restricted-sandbox"


def test_allowlisted_control_flow_renders(client: TestClient) -> None:
    body = "{% if order.status == 'shipped' %}shipped:{{ order.number }}{% endif %}"
    response = _post(client, body)
    assert response.status_code == 200, response.text
    assert response.json()["rendered"] == "shipped:1001"


@pytest.mark.parametrize(
    "payload",
    [
        "{{ config.integration_api_key }}",
        "{{ settings.SECRET_KEY }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ cycler.__init__.__globals__.os.popen('id').read() }}",
        "{{ range(5) }}",
        "{{ order.__class__ }}",
        "{% for x in ().__class__ %}{% endfor %}",
        "{{ order.number ",
    ],
)
def test_disallowed_constructs_are_rejected_generically(client: TestClient, payload: str) -> None:
    response = _post(client, payload)
    assert response.status_code == 400
    body = response.json()
    # Uniform, structure-free rejection: no engine/module/attribute detail, no names.
    assert body["detail"] == GENERIC_DETAIL
    text = response.text
    assert FICTIONAL_INTEGRATION_API_KEY not in text
    assert DEMO_SENTINEL not in text
    assert "order" not in text.lower()  # permitted name not enumerated
    assert "uid=" not in text


def test_rejection_emits_exactly_one_clean_audit_event(client: TestClient) -> None:
    with _capture_audit() as buffer:
        response = _post(client, "{{ config.integration_api_key }}")
    assert response.status_code == 400

    events = _audit_lines(buffer)
    assert len(events) == 1
    event = events[0]
    assert event["action"] == "notification.preview.restricted"
    assert event["outcome"] == "rejected"
    assert event["actor"] == "mallory"
    assert event["tenant"] == "globex"
    assert event["correlation_id"] == response.headers["X-Correlation-ID"]

    # The event must not leak tokens, secrets, the raw payload, or permitted names.
    raw = buffer.getvalue()
    assert GLOBEX_TOKEN not in raw
    assert FICTIONAL_INTEGRATION_API_KEY not in raw
    assert "integration_api_key" not in raw
    assert "Bearer" not in raw


def test_successful_render_emits_no_audit_event(client: TestClient) -> None:
    with _capture_audit() as buffer:
        response = _post(client, "{{ order.number }}")
    assert response.status_code == 200
    assert _audit_lines(buffer) == []


def test_correlation_id_present_on_success(client: TestClient) -> None:
    response = _post(client, "{{ order.status }}")
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID")


def test_restricted_path_is_tenant_scoped(client: TestClient) -> None:
    # Order 2001 belongs to another tenant: a 404, never data, and no audit event.
    with _capture_audit() as buffer:
        response = _post(client, "{{ order.number }}", order_reference="2001")
    assert response.status_code == 404
    assert _audit_lines(buffer) == []
