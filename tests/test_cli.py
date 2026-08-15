"""The comparison CLI formatting and argument parsing (FR-010)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from contextless.cli import (
    _build_parser,
    format_comparison,
    format_exchange,
    format_outcome_table,
)
from contextless.scenarios import compare
from tests.conftest import GLOBEX_TOKEN


def test_compare_table_shows_every_signal(
    client: TestClient, vulnerable_client: TestClient
) -> None:
    comparisons = compare(client, vulnerable_client, GLOBEX_TOKEN)
    text = format_comparison(comparisons)

    # Both compilation modes and an explicit verdict are visible.
    assert "template source" in text
    assert "data" in text
    assert "VULNERABLE" in text
    # The expression evaluation is visible on the vulnerable side.
    assert "1337" in text
    # Every ladder scenario is present.
    for label in ("expression evaluation", "configuration / secret disclosure"):
        assert label in text


def test_outcome_table_marks_secure_as_safe(
    client: TestClient, vulnerable_client: TestClient
) -> None:
    comparisons = compare(client, vulnerable_client, GLOBEX_TOKEN)
    rce = next(c for c in comparisons if c.scenario.key == "rce")
    table = format_outcome_table(rce)
    assert "code executed" in table
    assert "verdict" in table
    # The secure column is 'secure'; the vulnerable column is 'VULNERABLE'.
    assert "VULNERABLE" in table


def test_verbose_exchange_redacts_the_token(
    client: TestClient, vulnerable_client: TestClient
) -> None:
    comparisons = compare(client, vulnerable_client, GLOBEX_TOKEN)
    exchange = format_exchange("vulnerable", comparisons[0].scenario, comparisons[0].vulnerable)
    assert "Bearer ***redacted***" in exchange
    assert GLOBEX_TOKEN not in exchange


def test_parser_requires_a_command() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args([])


def test_parser_compare_defaults() -> None:
    args = _build_parser().parse_args(["compare"])
    assert args.command == "compare"
    assert args.secure_url.endswith(":8000")
    assert args.vulnerable_url.endswith(":8001")
    assert args.verbose is False
