"""Secure rendering: keep user data in the render context of a fixed template.

The primary fix never compiles user-supplied input as a template. Instead it
substitutes only an explicit allowlist of named placeholders with tenant-scoped
order **data**; every other placeholder or template-looking construct is
preserved verbatim as inert literal text. Because nothing is ever evaluated,
injected expressions, configuration reads, and object-graph payloads render as
literal characters — no expression evaluation, no secret disclosure, no command
execution.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from contextless.domain.models import Order

AllowlistResolver = Callable[[Order], str]

# The ONLY placeholders that resolve. Each maps to a value read from the in-scope
# order. Anything not listed here is left untouched.
ALLOWLIST: Mapping[str, AllowlistResolver] = {
    "order.number": lambda order: order.number,
    "order.customer_name": lambda order: order.customer.name,
    "order.status": lambda order: order.status,
}

# Matches ``{{ name }}`` only when ``name`` is exactly one allowlisted key
# (surrounding whitespace permitted). No expression grammar is honored.
_PLACEHOLDER = re.compile(
    r"\{\{\s*(" + "|".join(re.escape(name) for name in ALLOWLIST) + r")\s*\}\}"
)


def render_secure(body: str, order: Order) -> str:
    """Substitute allowlisted placeholders with order data; keep all else literal."""

    def _substitute(match: re.Match[str]) -> str:
        return ALLOWLIST[match.group(1)](order)

    return _PLACEHOLDER.sub(_substitute, body)
