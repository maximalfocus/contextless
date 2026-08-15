"""Defence-in-depth rendering: a sandboxed engine with an explicit name allowlist.

This is a *secondary* mitigation for the case where a product genuinely must let
users author template logic. It compiles the user body with a sandboxed Jinja2
engine that constrains attribute access, refuses undefined names, and exposes an
explicit allowlist of names. A disallowed construct is rejected wholesale.

It is **not** the primary control. Template-engine sandbox escapes are a recurring
vulnerability class, so untrusted template authoring should be avoided where the
data-into-context approach is sufficient.
"""

from __future__ import annotations

from jinja2 import StrictUndefined, meta
from jinja2.sandbox import SandboxedEnvironment

from contextless.domain.models import Order
from contextless.rendering.context import order_view

# The only names a restricted template may reference. Everything else — including
# Jinja globals such as ``range``/``cycler``/``lipsum`` and any configuration
# object — is disallowed.
ALLOWED_NAMES = frozenset({"order"})

_ENV = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)
# Explicit name allowlist: drop Jinja's ambient globals (range, cycler, lipsum,
# namespace, dict, joiner) so the only names a template can reference are those
# passed into the render context. Anything else is undefined and rejected.
_ENV.globals.clear()


class RestrictedRenderError(Exception):
    """A restricted-render request must be rejected generically."""


def render_restricted(body: str, order: Order) -> str:
    """Render a template through the sandbox, or raise ``RestrictedRenderError``.

    Rejection is deliberately uniform: the caller learns only that rendering was
    refused, never why, which names are permitted, or any engine internals.
    """
    try:
        ast = _ENV.parse(body)
    except Exception as exc:  # syntax errors and anything else: fail closed
        raise RestrictedRenderError from exc

    # Explicit name allowlist: reject any template referencing an unexposed name.
    if not meta.find_undeclared_variables(ast) <= ALLOWED_NAMES:
        raise RestrictedRenderError

    try:
        return _ENV.from_string(body).render(order=order_view(order))
    except Exception as exc:  # sandbox SecurityError, undefined access, etc.
        raise RestrictedRenderError from exc
