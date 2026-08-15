"""Request and response contracts shared by the application(s)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PreviewRequest(BaseModel):
    """A notification preview request: a body plus an order reference."""

    body: str = Field(description="Notification body, optionally using allowlisted placeholders.")
    order_reference: str = Field(description="Order number to render for the caller's tenant.")


class PreviewResponse(BaseModel):
    """The rendered notification and how it was produced."""

    rendered: str
    tenant: str
    order_reference: str
    render_mode: str
