"""Phase 1 end to end: traces -> induced skill -> human approval -> better behaviour.

Runs the identical task twice. The only thing that changes between the two runs is the
procedure text the agent is handed, so a fail-then-pass is evidence the induced skill
did the work.

    .venv\\Scripts\\python.exe scripts\\demo_phase1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Model output can contain characters the Windows console codepage cannot encode.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.agent import graph  # noqa: E402
from src.induction import engine, review  # noqa: E402
from src.memory import store  # noqa: E402
from src.skills.models import Skill  # noqa: E402
from src.traces import loader  # noqa: E402

TOPIC = "running-tests"
V1 = Skill(
    name="run-the-tests",
    topic=TOPIC,
    version=1,
    status="active",
    procedure=["Run pytest in the sandbox and report whether it passed."],
)


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def reset() -> None:
    """Put the repo back to its pre-demo state so this script is repeatable."""
    for path in store.TRACES.glob("run-*.json"):
        path.unlink()
    for path in store.PROPOSALS.glob("run-the-tests-*"):
        path.unlink()
    store.save_skill(V1)
    graph.reset_sandbox()


def main() -> int:
    reset()

    rule("0. seed traces")
    episodes = loader.load()
    failures = [e for e in episodes if e.outcome == "fail"]
    print(f"{len(episodes)} episodes for topic '{TOPIC}', {len(failures)} of them failures")

    rule("1. run the task with skill v1")
    print(f"procedure: {V1.procedure}")
    graph.reset_sandbox()
    first = graph.run_task(TOPIC)
    print(f"tools called: {[c.tool for c in first.episode.tool_calls] or 'none'}")
    print(f"agent says:   {first.answer.strip()[:300]}")
    print(f"outcome:      {first.episode.outcome.upper()}")

    rule("2. induce a better procedure from the traces")
    result = engine.induce(TOPIC)
    if result.proposal is None:
        print("induction produced nothing usable")
        print(f"dropped: {result.dropped}")
        return 1
    print(review.render(result.proposal))
    if result.dropped:
        print(f"\ndropped for missing provenance: {result.dropped}")

    rule("3. human review gate")
    pending = review.pending("run-the-tests")
    print(f"{len(pending)} proposal(s) awaiting review; approving v{result.proposal.version}")
    active = review.approve(result.proposal)
    print(f"active skill is now {active.name} v{active.version}")

    rule("4. run the identical task with the approved skill")
    graph.reset_sandbox()
    second = graph.run_task(TOPIC)
    print(f"tools called: {[c.tool for c in second.episode.tool_calls] or 'none'}")
    print(f"agent says:   {second.answer.strip()[:300]}")
    print(f"outcome:      {second.episode.outcome.upper()}")

    rule("verdict")
    print(f"v{first.skill_version}: {first.episode.outcome}    v{second.skill_version}: {second.episode.outcome}")
    if not first.passed and second.passed:
        print("\nPASS - the same task failed on v1 and passed on the induced v2")
        return 0
    if first.passed:
        print("\nINCONCLUSIVE - v1 already passed, so the task is not sensitive to the skill")
        return 1
    print("\nFAIL - v2 did not fix the task")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
