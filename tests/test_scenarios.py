"""The scenario engine classifies each app's behaviour (FR-010).

TestClient is an ``httpx.Client`` subclass, so the engine runs directly against
the in-process apps — no terminal input and no network.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from contextless.scenarios import SCENARIOS, compare, run_ladder
from tests.conftest import GLOBEX_TOKEN


def test_secure_ladder_is_all_secure(client: TestClient) -> None:
    outcomes = run_ladder(client, GLOBEX_TOKEN)
    assert [o.verdict for o in outcomes] == ["secure"] * len(SCENARIOS)
    for outcome in outcomes:
        assert outcome.compiled_as == "data"
        assert not outcome.expression_evaluated
        assert not outcome.secret_leaked
        assert not outcome.code_executed


def test_vulnerable_ladder_flags_each_signal(vulnerable_client: TestClient) -> None:
    outcomes = {o.scenario.key: o for o in run_ladder(vulnerable_client, GLOBEX_TOKEN)}
    assert all(o.compiled_as == "template source" for o in outcomes.values())
    assert outcomes["benign"].verdict == "secure"
    assert outcomes["expression"].expression_evaluated
    assert outcomes["secret"].secret_leaked
    assert outcomes["rce"].code_executed
    assert outcomes["rce"].verdict == "VULNERABLE"


def test_compare_pairs_scenarios(client: TestClient, vulnerable_client: TestClient) -> None:
    comparisons = compare(client, vulnerable_client, GLOBEX_TOKEN)
    assert len(comparisons) == len(SCENARIOS)

    benign = next(c for c in comparisons if c.scenario.key == "benign")
    assert benign.secure.rendered == benign.vulnerable.rendered  # identical legitimate output

    rce = next(c for c in comparisons if c.scenario.key == "rce")
    assert rce.secure.verdict == "secure"
    assert rce.vulnerable.verdict == "VULNERABLE"
