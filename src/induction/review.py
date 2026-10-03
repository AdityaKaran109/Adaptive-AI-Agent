"""Human gate: approve a proposal, or reject it with a reason.

Approval promotes the proposal to the active skill. Rejection stores the reason so the
next draft can use it. Nothing here approves automatically - the gate is the point.
"""

from __future__ import annotations

from src.memory import store
from src.skills import box
from src.skills.models import Skill


def pending(name: str | None = None) -> list[Skill]:
    proposals = store.list_proposals(status="awaiting_review")
    return [p for p in proposals if name is None or p.name == name]


def render(proposal: Skill) -> str:
    """What a reviewer reads before deciding."""
    lines = [f"{proposal.name} v{proposal.version}  ({proposal.status})", ""]
    for i, step in enumerate(proposal.procedure, 1):
        lines.append(f"  {i}. {step}")
    if proposal.provenance:
        lines += ["", "  evidence:"]
        for claim in proposal.provenance:
            lines.append(f"    - {', '.join(claim.episodes)}: {claim.evidence}")
    return "\n".join(lines)


def approve(proposal: Skill) -> Skill:
    """Promote the proposal to the active version of its skill."""
    active = box.promote(proposal)
    store.save_proposal(Skill(**{**proposal.model_dump(), "status": "active"}))
    return active


def reject(proposal: Skill, reason: str) -> Skill:
    """Keep the proposal out of the box, and remember why."""
    if not reason.strip():
        raise ValueError("a rejection needs a reason - the next draft reads it")
    rejected = Skill(**{**proposal.model_dump(), "status": "rejected", "rejection_reason": reason})
    store.save_proposal(rejected)
    return rejected
