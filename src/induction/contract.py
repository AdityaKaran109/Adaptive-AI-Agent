"""Instruction and output shape for the induction model.

Input: episodes for one topic. Output: steps, tools, errors, fixes, and provenance for
each claim. The schema is enforced, not requested: a response that does not fit fails
loudly rather than being coerced into something plausible.

Provenance is nested inside each step rather than sitting in a parallel list. An
earlier version had `steps` and `provenance` as two lists joined by matching the step
text, and a 4B model reliably wrote the episode ids into the step strings and left the
provenance list empty - so every step got dropped as uncited. Nesting makes a step
without citations impossible to express.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class InducedStep(BaseModel):
    """One procedure step, with the evidence that justifies it."""

    step: str = Field(description="One imperative sentence. No episode ids in this text.")
    episodes: list[str] = Field(
        description="Ids of episodes that justify this step, e.g. ['ep-001', 'ep-003']."
    )
    evidence: str = Field(description="Short quote or paraphrase of what those episodes show.")


class InducedSkill(BaseModel):
    """What the induction model must return."""

    steps: list[InducedStep] = Field(description="The procedure, in order.")
    tools: list[str] = Field(default_factory=list, description="Tool names the procedure uses.")
    errors: list[str] = Field(default_factory=list, description="Recurring errors observed.")
    fixes: list[str] = Field(default_factory=list, description="What resolved each error.")


INSTRUCTION = """\
You improve an agent's written procedure by reading what actually happened when it ran.

Current procedure for "{skill_name}" (version {version}):
{current}

{tools_line}
Episodes:
{episodes}

Write an improved procedure. Rules:
- Fix causes that repeat across episodes. Ignore one-off noise.
- Name the exact command or tool where one applies.
- Put prerequisites before the action that needs them.
- Respect any preference the user stated.
- Keep it to at most five steps. Each step is one imperative sentence.
- For each step, put the justifying episode ids in that step's "episodes" field.
  Cite ids exactly as they appear above. Never write an episode id inside the step text.
  A step you cannot cite will be discarded, so do not include one.
"""

AGENT_TOOLS = ["run_script", "run_tests", "list_dir", "read_file"]


def build_prompt(
    skill_name: str,
    version: int,
    current: list[str],
    episodes: list,
    tools: list[str] | None = None,
) -> str:
    """`tools` is domain-specific: the sandbox agent has some, a chat assistant has none."""
    names = AGENT_TOOLS if tools is None else tools
    current_text = (
        "\n".join(f"{i}. {s}" for i, s in enumerate(current, 1)) if current else "(empty)"
    )
    return INSTRUCTION.format(
        skill_name=skill_name,
        version=version,
        current=current_text,
        tools_line=f"Tools the agent can call: {', '.join(names)}\n" if names else "",
        episodes="\n\n".join(e.digest() for e in episodes),
    )
