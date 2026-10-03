"""Read and write traces, skills and proposals as files under data/.

Nothing here opens a network connection. This is the local stand-in for the course's
Oracle Agent Memory store, and it keeps Phase 1 testable without a database.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.skills.models import Skill
from src.traces.models import Episode

DATA = Path(__file__).resolve().parents[2] / "data"
TRACES = DATA / "traces"
SKILLS = DATA / "skills"
PROPOSALS = DATA / "proposals"


# --- traces ---------------------------------------------------------------


def load_episodes(topic: str | None = None) -> list[Episode]:
    episodes = [
        Episode.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(TRACES.glob("*.json"))
    ]
    return [e for e in episodes if topic is None or e.topic == topic]


def append_episode(episode: Episode) -> Path:
    TRACES.mkdir(parents=True, exist_ok=True)
    path = TRACES / f"{episode.episode_id}.json"
    path.write_text(episode.model_dump_json(indent=2), encoding="utf-8")
    return path


# --- skills ---------------------------------------------------------------


def load_skill(name: str) -> Skill | None:
    path = SKILLS / name / "SKILL.md"
    if not path.exists():
        return None
    return Skill.from_markdown(path.read_text(encoding="utf-8"))


def save_skill(skill: Skill) -> Path:
    path = SKILLS / skill.name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(skill.to_markdown(), encoding="utf-8")
    return path


# --- proposals ------------------------------------------------------------


def proposal_path(name: str, version: int) -> Path:
    return PROPOSALS / f"{name}-v{version}.md"


def save_proposal(skill: Skill) -> Path:
    PROPOSALS.mkdir(parents=True, exist_ok=True)
    path = proposal_path(skill.name, skill.version)
    path.write_text(skill.to_markdown(), encoding="utf-8")
    # Provenance is the audit trail for the human reviewer; keep the structured copy too.
    path.with_suffix(".json").write_text(skill.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_proposal(name: str, version: int) -> Skill | None:
    path = proposal_path(name, version).with_suffix(".json")
    if not path.exists():
        return None
    return Skill.model_validate_json(path.read_text(encoding="utf-8"))


def list_proposals(status: str | None = None) -> list[Skill]:
    if not PROPOSALS.exists():
        return []
    found = [
        Skill.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(PROPOSALS.glob("*.json"))
    ]
    return [s for s in found if status is None or s.status == status]
