"""Table-driven tests whose cases live in a generated fixture.

The fixture is deliberately not committed: running pytest without generating it first
fails at collection time. That missing prerequisite is the recurring failure the
induction step is supposed to notice in the traces.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shipping import shipping_cost  # noqa: E402

CASES_FILE = Path(__file__).resolve().parents[1] / ".cache" / "cases.json"

if not CASES_FILE.exists():
    # Deliberately not instructive: a real missing-file error does not tell you which
    # script produces the file. Knowing that is the job of the skill, not the error.
    pytest.fail(f"FileNotFoundError: {CASES_FILE}", pytrace=False)

CASES = json.loads(CASES_FILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_shipping_cost(case: dict) -> None:
    assert shipping_cost(case["weight_kg"], case["express"]) == pytest.approx(case["expected"])


def test_rejects_zero_weight() -> None:
    with pytest.raises(ValueError):
        shipping_cost(0)
