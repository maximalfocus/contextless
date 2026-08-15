"""ASGI entry point for the secure application."""

from __future__ import annotations

from contextless.apps.secure import create_secure_app

app = create_secure_app()
