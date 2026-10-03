"""Behaviour adaptation across chat sessions, on Oracle Agent Memory.

Five separate sessions. Each one is a cold thread - no history, nothing carried over -
and in each one a scripted user has to correct the assistant with the same project
specific fact. After the fifth, induction reads those five sessions back out of Agent
Memory, proposes a skill, and waits for approval. Then the same question is asked again.

Three conditions are measured, so the skill does not get credit for what plain memory
retrieval already does:

    cold     no memory, no skill   -> sessions 1-5
    memory   hybrid search only    -> session 6
    skill    approved procedure    -> session 7

    .venv\\Scripts\\python.exe scripts\\demo_chat_sessions.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Model output can contain characters the Windows console codepage cannot encode.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.chat import scenario  # noqa: E402
from src.chat.session import TOPIC, run_session  # noqa: E402
from src.induction import engine, review  # noqa: E402
from src.memory import agent_memory, store  # noqa: E402
from src.traces import from_memory  # noqa: E402

SKILL_NAME = "diagnose-build-failure"


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def short(text: str, n: int = 220) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= n else flat[:n] + "..."


def reset(memory) -> None:
    """Delete this user's past threads and the skill, so the script is repeatable."""
    for record in memory.list_threads(user_id=scenario.USER_ID, limit=200):
        memory.delete_thread(record.thread_id)
    shutil.rmtree(store.SKILLS / SKILL_NAME, ignore_errors=True)
    for path in store.PROPOSALS.glob(f"{SKILL_NAME}-*"):
        path.unlink()


def main() -> int:
    memory = agent_memory.connect()
    reset(memory)

    rule("1. five separate sessions, each one cold")
    print(f"the assistant has no skill for '{TOPIC}' and no history in any session\n")
    cold_hits = 0
    for i, exchange in enumerate(scenario.SESSIONS, 1):
        result = run_session(
            memory,
            user_id=scenario.USER_ID,
            question=exchange.question,
            correction=exchange.correction,
        )
        knew = result.knows(scenario.KEY_FACT)
        cold_hits += knew
        print(f"session {i} (thread {result.thread_id[:8]})")
        print(f"  user: {short(exchange.question, 100)}")
        print(f"  bot : {short(result.first_reply, 180)}")
        print(f"  -> mentioned '{scenario.KEY_FACT}' unprompted: {'YES' if knew else 'no'}")
        print(f"  user corrects it, and the correction is stored in Agent Memory\n")
    print(f"cold sessions that knew the fact: {cold_hits}/5")

    rule("2. read the sessions back out of Agent Memory as episodes")
    episodes = from_memory.episodes_for_user(memory, scenario.USER_ID, TOPIC)
    failed = [e for e in episodes if e.outcome == "fail"]
    print(f"{len(episodes)} episodes, {len(failed)} of them corrected by the user")
    print("\nwhat induction will read for one of them:\n")
    print(failed[0].digest() if failed else "(nothing)")

    rule("3. induce a skill from those five sessions")
    result = engine.induce(TOPIC, episodes=episodes, tools=[])
    if result.proposal is None:
        print(f"induction produced nothing usable; dropped={result.dropped}")
        return 1
    print(review.render(result.proposal))
    if result.dropped:
        print(f"\ndropped for missing provenance: {result.dropped}")

    rule("4. human review gate")
    active = review.approve(result.proposal)
    print(f"active skill is now {active.name} v{active.version}")
    print(f"written to {store.SKILLS / SKILL_NAME / 'SKILL.md'}")

    rule("5. ask the same question again in two fresh sessions")
    print(f"question: {short(scenario.EVAL_QUESTION, 120)}\n")

    raw_memory = run_session(
        memory,
        user_id=scenario.USER_ID,
        question=scenario.EVAL_QUESTION,
        use_memory=True,
        memory_filtered=False,
    )
    print("condition: memory, searching the raw transcript too")
    for snippet in raw_memory.retrieved or []:
        print(f"    retrieved: {short(snippet, 110)}")
    print(f"  bot : {short(raw_memory.first_reply, 200)}")
    print(f"  -> knows the fact: {'YES' if raw_memory.knows(scenario.KEY_FACT) else 'no'}\n")

    with_memory = run_session(
        memory,
        user_id=scenario.USER_ID,
        question=scenario.EVAL_QUESTION,
        use_memory=True,
    )
    print("condition: memory, filtered to distilled facts and guidelines")
    for snippet in with_memory.retrieved or []:
        print(f"    retrieved: {short(snippet, 110)}")
    print(f"  bot : {short(with_memory.first_reply, 200)}")
    print(f"  -> knows the fact: {'YES' if with_memory.knows(scenario.KEY_FACT) else 'no'}\n")

    with_skill = run_session(
        memory,
        user_id=scenario.USER_ID,
        question=scenario.EVAL_QUESTION,
        skill=active,
    )
    print("condition: approved skill (no memory lookup)")
    print(f"  bot : {short(with_skill.first_reply, 200)}")
    print(f"  -> knows the fact: {'YES' if with_skill.knows(scenario.KEY_FACT) else 'no'}")

    def verdict(result) -> str:
        return "knew it" if result.knows(scenario.KEY_FACT) else "did not"

    rule("verdict")
    print(f"cold,   no memory no skill : {cold_hits}/5 knew '{scenario.KEY_FACT}'")
    print(f"memory, raw transcript     : {verdict(raw_memory)}")
    print(f"memory, distilled facts    : {verdict(with_memory)}")
    print(f"skill,  approved procedure : {verdict(with_skill)}")

    if cold_hits > 0:
        print("\nINCONCLUSIVE - the base model already knew the fact, so nothing was learned")
        return 1
    if not with_skill.knows(scenario.KEY_FACT):
        print("\nFAIL - the approved skill did not carry the fact into a new session")
        return 1
    print("\nPASS - unknown in five cold sessions, known in a new session via the induced skill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
