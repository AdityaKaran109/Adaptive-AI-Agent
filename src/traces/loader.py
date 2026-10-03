"""Load synthetic episodes from data/traces/ into the store.

Hand-written rather than generated, so there is a known-good answer to check induction
against. The dominant signal is four episodes failing on the same missing fixture with
the same fix; there is also a weaker directory mistake and one stated preference, which
together test whether induction picks the repeated cause over the incidental noise.
"""

from __future__ import annotations

from src.memory import store
from src.traces.models import Episode, Failure, ToolCall, Turn

TOPIC = "running-tests"
MISSING_FIXTURE = (
    "ERROR collecting tests/test_shipping.py - FileNotFoundError: sandbox/.cache/cases.json"
)
FIXTURE_FIX = "Ran make_fixtures.py with run_script to create .cache/cases.json, then pytest passed."


def _episode(
    n: int,
    outcome: str,
    *,
    steps: list[str],
    calls: list[ToolCall],
    failures: list[Failure] | None = None,
    preferences: list[str] | None = None,
    turns: list[Turn] | None = None,
) -> Episode:
    return Episode(
        episode_id=f"ep-{n:03d}",
        topic=TOPIC,
        task="Run the sandbox test suite and report the result.",
        outcome=outcome,
        skill_used="run-the-tests",
        skill_version=1,
        steps=steps,
        tool_calls=calls,
        failures=failures or [],
        preferences=preferences or [],
        turns=turns or [],
    )


def synthetic_episodes() -> list[Episode]:
    fail_on_fixture = [
        _episode(
            n,
            "fail",
            steps=["run pytest"],
            calls=[ToolCall(tool="run_tests", ok=False, output=MISSING_FIXTURE)],
            failures=[Failure(error=MISSING_FIXTURE, fix=FIXTURE_FIX)],
        )
        for n in (1, 3, 4, 7)
    ]

    passed = [
        _episode(
            n,
            "pass",
            steps=["run make_fixtures.py", "run pytest"],
            calls=[
                ToolCall(tool="run_script", args={"name": "make_fixtures.py"}, ok=True, output="wrote .cache/cases.json"),
                ToolCall(tool="run_tests", ok=True, output="6 passed in 0.01s"),
            ],
        )
        for n in (2, 6)
    ]

    wrong_dir = _episode(
        5,
        "fail",
        steps=["run pytest from the repository root"],
        calls=[ToolCall(tool="run_tests", args={"cwd": "."}, ok=False, output="collected 0 items")],
        failures=[
            Failure(
                error="pytest collected 0 items when run from the repository root",
                fix="Ran pytest from the sandbox directory instead.",
            )
        ],
    )

    with_preference = _episode(
        8,
        "pass",
        steps=["run make_fixtures.py", "run pytest", "report counts"],
        calls=[
            ToolCall(tool="run_script", args={"name": "make_fixtures.py"}, ok=True, output="wrote .cache/cases.json"),
            ToolCall(tool="run_tests", ok=True, output="6 passed in 0.01s"),
        ],
        preferences=["Report only the pass/fail counts, not the full pytest output."],
        turns=[
            Turn(role="user", content="Just give me the counts next time, not the whole log."),
            Turn(role="assistant", content="Understood - 6 passed, 0 failed."),
        ],
    )

    return sorted(
        [*fail_on_fixture, *passed, wrong_dir, with_preference], key=lambda e: e.episode_id
    )


def load() -> list[Episode]:
    """Write the synthetic episodes to data/traces/ and return them."""
    episodes = synthetic_episodes()
    for episode in episodes:
        store.append_episode(episode)
    return episodes


if __name__ == "__main__":
    written = load()
    print(f"wrote {len(written)} episodes to {store.TRACES}")
