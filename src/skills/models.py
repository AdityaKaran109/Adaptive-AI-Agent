"""A skill version: name, topic, procedure, version and status.

Stored as SKILL.md - frontmatter plus a numbered procedure - because a human has to
read and approve each proposal. Only one version of a skill is ever active.
"""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, Field

Status = Literal["active", "awaiting_review", "rejected"]


class Claim(BaseModel):
    """One procedure step and the episodes that justify it."""

    step: str
    episodes: list[str] = Field(default_factory=list)
    evidence: str = ""


class Skill(BaseModel):
    name: str
    topic: str
    version: int
    status: Status
    procedure: list[str]
    provenance: list[Claim] = Field(default_factory=list)
    rejection_reason: str | None = None

    def to_markdown(self) -> str:
        front = {
            "name": self.name,
            "topic": self.topic,
            "version": self.version,
            "status": self.status,
        }
        if self.rejection_reason:
            front["rejection_reason"] = self.rejection_reason
        out = ["---", yaml.safe_dump(front, sort_keys=False).strip(), "---", "", "## Procedure", ""]
        out += [f"{i}. {step}" for i, step in enumerate(self.procedure, 1)]
        if self.provenance:
            out += ["", "## Provenance", ""]
            for claim in self.provenance:
                cited = ", ".join(claim.episodes) or "none"
                out.append(f"- **{claim.step}** — {claim.evidence} _(episodes: {cited})_")
        return "\n".join(out) + "\n"

    @classmethod
    def from_markdown(cls, text: str) -> Skill:
        _, raw_front, body = text.split("---", 2)
        front = yaml.safe_load(raw_front) or {}
        procedure: list[str] = []
        in_procedure = False
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                in_procedure = stripped == "## Procedure"
                continue
            if in_procedure and stripped and stripped[0].isdigit():
                procedure.append(stripped.split(". ", 1)[-1])
        return cls(
            name=front["name"],
            topic=front.get("topic", front["name"]),
            version=int(front["version"]),
            status=front.get("status", "active"),
            procedure=procedure,
            rejection_reason=front.get("rejection_reason"),
        )
