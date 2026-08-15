"""The secure notification application.

Exposes the same method, path, authentication contract, and success shape as the
(later) vulnerable app, but renders through the data-into-context fix so no
injected construct is ever evaluated.
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from contextless.auth import authenticate
from contextless.db import build_seeded_engine, get_session
from contextless.domain.models import Order, User
from contextless.logging_setup import configure_logging, emit_audit_event
from contextless.rendering.restricted import RestrictedRenderError, render_restricted
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

    def _load_order(session: Session, user: User, order_reference: str) -> Order:
        order = session.scalar(
            select(Order).where(
                Order.tenant_id == user.tenant_id,
                Order.number == order_reference,
            )
        )
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return order

    @app.post("/notifications/preview", response_model=PreviewResponse)
    def preview(
        payload: PreviewRequest,
        user: Annotated[User, Depends(authenticate)],
        session: Annotated[Session, Depends(get_session)],
    ) -> PreviewResponse:
        order = _load_order(session, user, payload.order_reference)
        return PreviewResponse(
            rendered=render_secure(payload.body, order),
            tenant=user.tenant.slug,
            order_reference=order.number,
            render_mode="data-into-context",
        )

    @app.post("/notifications/preview/restricted", response_model=PreviewResponse)
    def preview_restricted(
        payload: PreviewRequest,
        user: Annotated[User, Depends(authenticate)],
        session: Annotated[Session, Depends(get_session)],
        response: Response,
    ) -> PreviewResponse:
        order = _load_order(session, user, payload.order_reference)
        correlation_id = uuid4().hex
        response.headers["X-Correlation-ID"] = correlation_id
        try:
            rendered = render_restricted(payload.body, order)
        except RestrictedRenderError:
            emit_audit_event(
                action="notification.preview.restricted",
                outcome="rejected",
                correlation_id=correlation_id,
                actor=user.username,
                tenant=user.tenant.slug,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The notification template could not be rendered.",
                headers={"X-Correlation-ID": correlation_id},
            ) from None
        return PreviewResponse(
            rendered=rendered,
            tenant=user.tenant.slug,
            order_reference=order.number,
            render_mode="restricted-sandbox",
        )

    return app
