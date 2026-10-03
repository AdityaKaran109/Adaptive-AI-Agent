"""Draft an enhanced skill from traces and write it to data/proposals/.

The proposal stays inactive until a human reviews it. Steps the model cannot tie to a
real episode are dropped before the proposal is written - unprovenanced claims are the
main failure mode of a small local model, so they are filtered here rather than trusted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from src.induction.contract import InducedSkill, build_prompt
from src.llm import client
from src.memory import store
from src.skills import box
from src.skills.models import Claim, Skill
from src.traces.models import Episode


@dataclass
class InductionResult:
    proposal: Skill | None
    dropped: list[str] = field(default_factory=list)
    raw: InducedSkill | None = None


def _cited(step, valid_ids: set[str]) -> Claim | None:
    """Keep a step only if it cites at least one episode that really exists."""
    episodes = [e for e in step.episodes if e in valid_ids]
    if not episodes:
        return None
    return Claim(step=step.step, episodes=episodes, evidence=step.evidence)


def induce(
    topic: str,
    *,
    model: str | None = None,
    episodes: list[Episode] | None = None,
    tools: list[str] | None = None,
) -> InductionResult:
    """Read the episodes for one topic and propose the next version of its skill.

    `episodes` lets the caller supply them from somewhere other than data/traces/ - the
    chat demo passes in sessions read back out of Oracle Agent Memory.
    """
    episodes = episodes if episodes is not None else store.load_episodes(topic)
    if not episodes:
        return InductionResult(proposal=None, dropped=["no episodes for this topic"])

    active = box.retrieve(topic)
    name = box.TOPIC_TO_SKILL.get(topic, topic)
    current = active.procedure if active else []
    version = (active.version if active else 0) + 1

    prompt = build_prompt(name, active.version if active else 0, current, episodes, tools)
    llm = client.structured(InducedSkill, model or os.environ.get("INDUCTION_MODEL"))
    induced: InducedSkill = llm.invoke(prompt)

    valid_ids = {e.episode_id for e in episodes}

    procedure: list[str] = []
    provenance: list[Claim] = []
    dropped: list[str] = []
    for step in induced.steps:
        claim = _cited(step, valid_ids)
        if claim is None:
            dropped.append(step.step)
            continue
        procedure.append(step.step)
        provenance.append(claim)

    if not procedure:
        return InductionResult(proposal=None, dropped=dropped, raw=induced)

    proposal = Skill(
        name=name,
        topic=topic,
        version=version,
        status="awaiting_review",
        procedure=procedure,
        provenance=provenance,
    )
    store.save_proposal(proposal)
    return InductionResult(proposal=proposal, dropped=dropped, raw=induced)
