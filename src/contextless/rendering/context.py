"""Shared render-context helpers.

Both applications render the same benign notification fields, so a single view of
the order guarantees byte-for-byte identical legitimate output across them.
"""

from __future__ import annotations

from types import SimpleNamespace

from contextless.domain.models import Order


def order_view(order: Order) -> SimpleNamespace:
    """A minimal view exposing exactly the notification's order fields."""
    return SimpleNamespace(
        number=order.number,
        customer_name=order.customer.name,
        status=order.status,
    )
