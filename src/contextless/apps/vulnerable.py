"""The intentionally vulnerable notification application (local demo only).

This app compiles user input as a template. It is dangerous by design and refuses
to start unless the operator explicitly acknowledges the risk with
``ALLOW_VULNERABLE_DEMO=true`` — the second of two deliberate opt-in actions (the
first being its opt-in Compose profile).
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from contextless.auth import authenticate
from contextless.db import build_seeded_engine, get_session
from contextless.domain.models import Order, User
from contextless.logging_setup import configure_logging
from contextless.rendering.vulnerable import render_vulnerable
from contextless.schemas import PreviewRequest, PreviewResponse

ALLOW_ENV = "ALLOW_VULNERABLE_DEMO"


class VulnerableDemoNotAllowed(RuntimeError):
    """Raised when the vulnerable app is started without explicit acknowledgement."""


def create_vulnerable_app() -> FastAPI:
    """Build the vulnerable app, or refuse without explicit acknowledgement."""
    if os.environ.get(ALLOW_ENV) != "true":
        raise VulnerableDemoNotAllowed(
            f"Refusing to start the vulnerable demo without {ALLOW_ENV}=true."
        )

    configure_logging()
    app = FastAPI(
        title="contextless (VULNERABLE — local educational demo only)",
        summary="Intentionally vulnerable: compiles user input as a template. Never deploy.",
        version="0.1.0",
    )
    app.state.engine = build_seeded_engine()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/notifications/preview", response_model=PreviewResponse)
    def preview(
        payload: PreviewRequest,
        user: Annotated[User, Depends(authenticate)],
        session: Annotated[Session, Depends(get_session)],
    ) -> PreviewResponse:
        order = session.scalar(
            select(Order).where(
                Order.tenant_id == user.tenant_id,
                Order.number == payload.order_reference,
            )
        )
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return PreviewResponse(
            rendered=render_vulnerable(payload.body, order),
            tenant=user.tenant.slug,
            order_reference=order.number,
            render_mode="template-source",
        )

    return app
