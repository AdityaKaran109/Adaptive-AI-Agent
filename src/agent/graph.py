"""LangGraph loop for one task.

Retrieve the active skill, call tools, and append the episode to the store. The same
task should fail on run-the-tests v1 and pass after v2 is approved - the only thing
that changes between the two runs is the procedure text the agent is handed.
"""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from src.agent import tools
from src.llm import client
from src.memory import store
from src.skills import box
from src.traces.models import Episode

TASK = "Run the sandbox test suite and report the result."

SYSTEM = """\
You are a coding agent working in a sandbox. Use the tools to do the task.

{skill}

Call the tools you need, then state the outcome in one line: how many tests passed and
how many failed. Do not guess the result - it must come from a tool.
"""

NO_SKILL = "You have no stored procedure for this task. Work it out from the tools."


@dataclass
class RunResult:
    episode: Episode
    answer: str
    skill_version: int | None
    passed: bool


def _render_skill(skill) -> str:
    if skill is None:
        return NO_SKILL
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(skill.procedure, 1))
    return f"Follow this procedure ({skill.name} v{skill.version}):\n{steps}"


def reset_sandbox() -> None:
    """Remove generated fixtures so each run genuinely needs the prerequisite step."""
    shutil.rmtree(tools.SANDBOX / ".cache", ignore_errors=True)


def run_task(topic: str = "running-tests", *, model: str | None = None) -> RunResult:
    skill = box.retrieve(topic)
    tools.reset()

    agent = create_react_agent(client.chat(model), tools.ALL)
    state = agent.invoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM.format(skill=_render_skill(skill))),
                HumanMessage(content=TASK),
            ]
        },
        {"recursion_limit": 25},
    )
    answer = state["messages"][-1].content

    calls = list(tools.CALLS)
    test_runs = [c for c in calls if c.tool == "run_tests"]
    passed = bool(test_runs) and test_runs[-1].ok

    episode = Episode(
        episode_id=f"run-{uuid.uuid4().hex[:8]}",
        topic=topic,
        task=TASK,
        outcome="pass" if passed else "fail",
        skill_used=skill.name if skill else None,
        skill_version=skill.version if skill else None,
        steps=[c.tool for c in calls],
        tool_calls=calls,
        failures=[],
    )
    store.append_episode(episode)

    return RunResult(
        episode=episode,
        answer=answer,
        skill_version=skill.version if skill else None,
        passed=passed,
    )
