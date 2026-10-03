"""Turn Oracle Agent Memory threads into Episodes the induction engine can read.

The chat case has no tool calls, so the error/fix signal comes from somewhere else: a
user correcting the assistant. A session the user had to correct is a failed episode,
and the correction is the fix. With that mapping, the same induction engine written for
the sandbox task works unchanged on conversations.
"""

from __future__ import annotations

from src.chat.session import TOPIC
from src.traces.models import Episode, Failure, Turn


def _turns(messages) -> list[Turn]:
    return [
        Turn(role=m.role, content=(m.content or "").strip())
        for m in messages
        if m.role in ("user", "assistant") and (m.content or "").strip()
    ]


def episode_from_thread(memory, thread_id: str, episode_id: str, topic: str = TOPIC) -> Episode | None:
    """One session -> one episode. Returns None for a thread with nothing usable in it."""
    messages = memory.get_thread(thread_id).get_messages()
    turns = _turns(messages)
    if len(turns) < 2:
        return None

    question = turns[0].content
    first_reply = turns[1].content

    # A third turn from the user means the first answer was wrong and got corrected.
    corrections = [t.content for t in turns[2:] if t.role == "user"]
    failures = [
        Failure(
            error=f"First answer was wrong: {first_reply[:200]}",
            fix=correction,
        )
        for correction in corrections
    ]

    return Episode(
        episode_id=episode_id,
        topic=topic,
        task=question,
        outcome="fail" if failures else "pass",
        skill_used=None,
        turns=turns,
        steps=[],
        failures=failures,
        preferences=[],
    )


def episodes_for_user(memory, user_id: str, topic: str = TOPIC) -> list[Episode]:
    """Every session this user has had on `topic`, oldest first, as episodes."""
    records = [
        r
        for r in memory.list_threads(user_id=user_id, limit=200)
        if (r.metadata or {}).get("topic") == topic
    ]
    records.sort(key=lambda r: r.timestamp)

    episodes: list[Episode] = []
    for i, record in enumerate(records, 1):
        episode = episode_from_thread(memory, record.thread_id, f"sess-{i:03d}", topic)
        if episode is not None:
            episodes.append(episode)
    return episodes
