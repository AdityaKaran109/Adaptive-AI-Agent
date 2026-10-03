"""One chat session with the assistant, stored as an Oracle Agent Memory thread.

A session is deliberately cold: a new thread, no history, nothing carried over from the
last one. That is what makes the demo honest - whatever the bot knows in its first reply
came either from the base model, from a memory lookup, or from an approved skill, and the
three can be switched on and off independently.

The "user" here is scripted, not a real person. The point is not to measure a human
conversation but to produce the same repeated correction five times over, which is the
input skill induction is supposed to learn from.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from oracleagentmemory.apis.searchscope import SearchScope

from src.llm import client
from src.skills.models import Skill

TOPIC = "build-failures"
AGENT_ID = "acme-helper"

SYSTEM = """\
You are an engineering assistant for the Acme orders service.

{skill}
{context}
Answer the user's question in at most three sentences. Be concrete: if a command fixes
the problem, give the command.
"""

NO_SKILL = "You have no stored procedure for this kind of question."
NO_CONTEXT = ""


@dataclass
class SessionResult:
    thread_id: str
    question: str
    first_reply: str
    corrected: bool
    final_reply: str | None = None
    retrieved: list[str] | None = None

    def knows(self, fact: str) -> bool:
        """Did the bot produce the project-specific fact in its FIRST reply?

        First reply only. After a correction the fact is in the context, so a later
        reply proves nothing about what the bot knew when the session opened.
        """
        return fact.lower() in self.first_reply.lower()


def _skill_block(skill: Skill | None) -> str:
    if skill is None:
        return NO_SKILL
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(skill.procedure, 1))
    return f"Follow this procedure ({skill.name} v{skill.version}):\n{steps}"


#": Restrict retrieval to what Agent Memory distilled, not the raw transcript.
# Unfiltered, the nearest neighbours of a question are other people's *questions* -
# semantically almost identical and useless as answers.
MEMORY_RECORD_TYPES = ["fact", "guideline", "preference"]


def _context_block(
    memory,
    user_id: str,
    question: str,
    max_results: int = 6,
    record_types: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Hybrid search over past sessions. `record_types=None` searches the raw transcript too."""
    kwargs = {"record_types": record_types} if record_types else {}
    results = memory.search(
        query=question,
        scope=SearchScope(user_id=user_id),
        max_results=max_results,
        **kwargs,
    )
    snippets = [(r.content or "").strip() for r in results if (r.content or "").strip()]
    if not snippets:
        return NO_CONTEXT, []
    listed = "\n".join(f"- {s}" for s in snippets)
    return f"\nWhat you remember from earlier sessions:\n{listed}\n", snippets


def run_session(
    memory,
    *,
    user_id: str,
    question: str,
    correction: str | None = None,
    skill: Skill | None = None,
    use_memory: bool = False,
    memory_filtered: bool = True,
    model: str | None = None,
) -> SessionResult:
    """Open a fresh thread, ask one question, optionally let the user correct the answer.

    `memory_filtered` picks the retrieval config: True searches only what Agent Memory
    distilled, False searches the raw transcript as well.
    """
    record_types = MEMORY_RECORD_TYPES if memory_filtered else None
    context, retrieved = (
        _context_block(memory, user_id, question, record_types=record_types)
        if use_memory
        else (NO_CONTEXT, [])
    )
    thread = memory.create_thread(
        user_id=user_id,
        agent_id=AGENT_ID,
        metadata={"topic": TOPIC, "corrected": bool(correction)},
    )

    llm = client.chat(model)
    system = SystemMessage(content=SYSTEM.format(skill=_skill_block(skill), context=context))
    first = llm.invoke([system, HumanMessage(content=question)]).content.strip()

    turns = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": first},
    ]
    final = None
    if correction:
        final = llm.invoke(
            [
                system,
                HumanMessage(content=question),
                AIMessage(content=first),
                HumanMessage(content=correction),
            ]
        ).content.strip()
        turns += [
            {"role": "user", "content": correction},
            {"role": "assistant", "content": final},
        ]

    thread.add_messages(turns)
    # Extraction runs on a background worker; without this the next session's lookup
    # can race it and find nothing.
    thread.wait_for_memory_extraction()

    return SessionResult(
        thread_id=thread.thread_id,
        question=question,
        first_reply=first,
        corrected=bool(correction),
        final_reply=final,
        retrieved=retrieved,
    )
