"""Application configuration reachable only through code.

This module holds a conspicuously fictional third-party integration secret and a
planted ``DEMO_SENTINEL`` marker. Neither value is a real credential; they grant
no access to anything. No legitimate notification ever needs them.

They exist so that a *later* vulnerable contrast can make context disclosure and
in-container code-execution reach observable. The secure application never places
these values into any render context, so they can never appear in its output.
"""

from __future__ import annotations

from dataclasses import dataclass

# A conspicuously fake "secret". It is demonstration-only and unlocks nothing.
FICTIONAL_INTEGRATION_API_KEY = "sk-demo-INTEGRATION-0000-NOT-A-REAL-SECRET"

# A harmless planted marker used only to give a later code-execution proof an
# unambiguous, meaningless thing to reach.
DEMO_SENTINEL = "CONTEXTLESS-DEMO-SENTINEL-2f9c1a7d"


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration held only in code."""

    integration_api_key: str = FICTIONAL_INTEGRATION_API_KEY
    demo_sentinel: str = DEMO_SENTINEL


APP_CONFIG = AppConfig()
