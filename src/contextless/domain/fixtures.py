"""Deterministic fixtures for the fictional notification domain.

Seeding produces identical data on every run so rendered output, counts, and
ordering are stable. Nothing here is a real organization, person, or credential.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from contextless.domain.models import Base, Customer, Order, Tenant, User

# Demo-only static bearer tokens. Conspicuously fake; they authenticate nothing
# outside this local demonstration.
GLOBEX_TOKEN = "demo-token-globex-mallory"
INITECH_TOKEN = "demo-token-initech-peter"


def seed(session: Session) -> None:
    """Create the schema and insert the deterministic fixture rows."""
    Base.metadata.create_all(session.get_bind())

    tenants = [
        Tenant(id=1, slug="globex", name="Globex Corporation"),
        Tenant(id=2, slug="initech", name="Initech LLC"),
    ]
    users = [
        User(id=1, tenant_id=1, username="mallory", token=GLOBEX_TOKEN),
        User(id=2, tenant_id=2, username="peter", token=INITECH_TOKEN),
    ]
    customers = [
        Customer(id=1, tenant_id=1, name="Alice Anderson"),
        Customer(id=2, tenant_id=1, name="Grace Hopper"),
        Customer(id=3, tenant_id=2, name="Bob Brown"),
    ]
    orders = [
        Order(id=1, tenant_id=1, number="1001", customer_id=1, status="shipped"),
        Order(id=2, tenant_id=1, number="1002", customer_id=2, status="processing"),
        Order(id=3, tenant_id=2, number="2001", customer_id=3, status="delivered"),
    ]

    session.add_all([*tenants, *users, *customers, *orders])
    session.commit()
