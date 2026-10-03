"""One agent episode: the record the induction engine reads.

These are the fields the lesson breaks a trajectory into. Episodes are the only
evidence induction is allowed to cite, so every one carries a stable `episode_id`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ToolCall(BaseModel):
    tool: str
    args: dict = Field(default_factory=dict)
    ok: bool
    output: str = ""


class Failure(BaseModel):
    """An error the agent hit, and what resolved it. The signal induction looks for."""

    error: str
    fix: str = ""


class Episode(BaseModel):
    episode_id: str
    topic: str
    task: str
    outcome: Literal["pass", "fail"]
    skill_used: str | None = None
    skill_version: int | None = None
    turns: list[Turn] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    failures: list[Failure] = Field(default_factory=list)

    def digest(self) -> str:
        """Compact rendering for the induction prompt - full JSON wastes the context."""
        lines = [f"episode {self.episode_id} | task: {self.task} | outcome: {self.outcome}"]
        if self.steps:
            lines.append("  steps: " + " -> ".join(self.steps))
        for call in self.tool_calls:
            lines.append(f"  tool {call.tool}({call.args}) -> {'ok' if call.ok else 'FAILED'}")
            if not call.ok and call.output:
                # A real run carries its error only in the tool output; induction needs it.
                lines.append(f"    output: {call.output.splitlines()[-1][:200]}")
        for failure in self.failures:
            lines.append(f"  error: {failure.error}")
            if failure.fix:
                lines.append(f"  fix:   {failure.fix}")
        for pref in self.preferences:
            lines.append(f"  preference: {pref}")
        return "\n".join(lines)
