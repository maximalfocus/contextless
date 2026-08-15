"""Vulnerable rendering: compiles the caller's body as template SOURCE.

This is the flaw, deliberately. User input is handed to the Jinja2 compiler and
executed on the server with the order **and** the application configuration (the
fictional integration secret and planted ``DEMO_SENTINEL``) in the render
namespace. That makes expression evaluation, context/secret disclosure, and
object-graph traversal to in-container code execution possible.

This module exists only for local demonstration. It must never be deployed.
"""

from __future__ import annotations

from jinja2 import Environment

from contextless.config import APP_CONFIG
from contextless.domain.models import Order
from contextless.rendering.context import order_view

# Intentionally NOT a SandboxedEnvironment and NOT autoescaped: the whole point of
# the demonstration is that the body is compiled and executed as template source.
_ENV = Environment(autoescape=False)


def render_vulnerable(body: str, order: Order) -> str:
    """Compile the user body as a template and render it — the vulnerability.

    The order view exposes the same benign fields as the secure app (so legitimate
    output is identical), while ``config`` in the namespace and the ambient globals
    make secret disclosure and object-graph code execution reachable.
    """
    template = _ENV.from_string(body)
    return template.render(order=order_view(order), config=APP_CONFIG)
