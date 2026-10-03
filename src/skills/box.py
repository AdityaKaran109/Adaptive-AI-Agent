"""Retrieve the active skill for a topic, and promote a reviewed version.

Promotion replaces the previous active version. A rejected proposal stays out of the
box and keeps the reviewer's reason so the next draft can use it.
"""

from __future__ import annotations

from src.memory import store
from src.skills.models import Skill

# Topics map to skill directories under data/skills/.
TOPIC_TO_SKILL = {
    "running-tests": "run-the-tests",
    "build-failures": "diagnose-build-failure",
}


def retrieve(topic: str) -> Skill | None:
    """The one active skill for a topic, or None if the box has nothing for it."""
    name = TOPIC_TO_SKILL.get(topic, topic)
    skill = store.load_skill(name)
    if skill is None or skill.status != "active":
        return None
    return skill


def promote(proposal: Skill) -> Skill:
    """Make an approved proposal the active version, replacing whatever was active."""
    if proposal.status != "awaiting_review":
        raise ValueError(f"only a proposal awaiting review can be promoted, got {proposal.status}")
    active = Skill(**{**proposal.model_dump(), "status": "active"})
    store.save_skill(active)
    return active
