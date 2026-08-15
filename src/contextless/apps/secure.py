"""The secure notification application.

Exposes the same method, path, authentication contract, and success shape as the
(later) vulnerable app, but renders through the data-into-context fix so no
injected construct is ever evaluated.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from contextless.auth import authenticate
from contextless.db import build_seeded_engine, get_session
from contextless.domain.models import Order, User
from contextless.logging_setup import configure_logging
from contextless.rendering.secure import render_secure
from contextless.schemas import PreviewRequest, PreviewResponse


def create_secure_app() -> FastAPI:
    """Build and return the secure FastAPI application."""
    configure_logging()

    app = FastAPI(
        title="contextless (secure)",
        summary="Educational SSTI demo — secure app: user data stays in the render context.",
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
            rendered=render_secure(payload.body, order),
            tenant=user.tenant.slug,
            order_reference=order.number,
            render_mode="data-into-context",
        )

    return app
