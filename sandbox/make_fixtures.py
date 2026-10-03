"""Generate the test fixture the sandbox suite needs.

Separate from the tests on purpose: it is the prerequisite step an agent only knows
about if its skill tells it to run this first.
"""

from __future__ import annotations

import json
from pathlib import Path

from shipping import shipping_cost

CASES = [
    {"id": "light", "weight_kg": 1.0, "express": False},
    {"id": "light-express", "weight_kg": 1.0, "express": True},
    {"id": "medium", "weight_kg": 12.5, "express": False},
    {"id": "medium-express", "weight_kg": 12.5, "express": True},
    {"id": "heavy-free", "weight_kg": 64.0, "express": False},
]


def main() -> Path:
    out = Path(__file__).resolve().parent / ".cache" / "cases.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    cases = [dict(c, expected=shipping_cost(c["weight_kg"], c["express"])) for c in CASES]
    out.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(f"wrote {main()}")
