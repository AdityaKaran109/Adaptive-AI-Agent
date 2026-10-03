"""Deterministic tests for the Phase 1 pipeline - no model calls.

The model-dependent part is covered by scripts/demo_phase1.py, which asserts the real
exit gate (same task fails on v1, passes on the induced v2). These tests cover the
machinery around it, so a regression there does not need an LLM to surface.
"""

from __future__ import annotations

import pytest

from src.induction.contract import InducedSkill, InducedStep, build_prompt
from src.induction.engine import _cited
from src.skills import box
from src.skills.models import Claim, Skill
from src.traces import loader
from src.traces.models import Episode, Failure, ToolCall


def make_skill(**kw) -> Skill:
    defaults = dict(
        name="run-the-tests",
        topic="running-tests",
        version=1,
        status="active",
        procedure=["Run pytest.", "Report the counts."],
    )
    return Skill(**{**defaults, **kw})


class TestSkillSerialisation:
    def test_markdown_round_trip(self):
        skill = make_skill(version=3)
        restored = Skill.from_markdown(skill.to_markdown())
        assert restored.name == skill.name
        assert restored.version == 3
        assert restored.procedure == skill.procedure

    def test_frontmatter_carries_status(self):
        md = make_skill(status="awaiting_review").to_markdown()
        assert "status: awaiting_review" in md

    def test_provenance_rendered_for_the_reviewer(self):
        skill = make_skill(
            provenance=[Claim(step="Run pytest.", episodes=["ep-001"], evidence="it failed here")]
        )
        assert "ep-001" in skill.to_markdown()
        assert "it failed here" in skill.to_markdown()


class TestProvenanceFilter:
    def test_keeps_a_step_citing_a_real_episode(self):
        step = InducedStep(step="Run make_fixtures.py.", episodes=["ep-001"], evidence="x")
        claim = _cited(step, {"ep-001", "ep-002"})
        assert claim is not None
        assert claim.episodes == ["ep-001"]

    def test_drops_an_uncited_step(self):
        step = InducedStep(step="Reboot the server.", episodes=[], evidence="")
        assert _cited(step, {"ep-001"}) is None

    def test_drops_invented_episode_ids(self):
        step = InducedStep(step="Do a thing.", episodes=["ep-999"], evidence="made up")
        assert _cited(step, {"ep-001"}) is None

    def test_keeps_only_the_real_ids_from_a_mixed_citation(self):
        step = InducedStep(step="Do a thing.", episodes=["ep-001", "ep-999"], evidence="partly")
        claim = _cited(step, {"ep-001"})
        assert claim is not None
        assert claim.episodes == ["ep-001"]


class TestPromotion:
    def test_promote_makes_a_proposal_active(self, tmp_path, monkeypatch):
        from src.memory import store

        monkeypatch.setattr(store, "SKILLS", tmp_path / "skills")
        proposal = make_skill(version=2, status="awaiting_review")
        active = box.promote(proposal)
        assert active.status == "active"
        assert active.version == 2

    def test_promote_refuses_an_already_active_skill(self):
        with pytest.raises(ValueError, match="awaiting review"):
            box.promote(make_skill(status="active"))


class TestTraces:
    def test_synthetic_set_has_a_dominant_repeated_failure(self):
        episodes = loader.synthetic_episodes()
        same_error = [
            e for e in episodes if any(loader.MISSING_FIXTURE in f.error for f in e.failures)
        ]
        assert len(same_error) >= 3, "induction needs a repeated cause to find"
        assert all(f.fix for e in same_error for f in e.failures)

    def test_episode_ids_are_unique(self):
        ids = [e.episode_id for e in loader.synthetic_episodes()]
        assert len(ids) == len(set(ids))

    def test_digest_surfaces_the_error_of_a_failed_tool_call(self):
        episode = Episode(
            episode_id="ep-x",
            topic="t",
            task="task",
            outcome="fail",
            tool_calls=[ToolCall(tool="run_tests", ok=False, output="boom: missing file")],
            failures=[Failure(error="boom", fix="")],
        )
        assert "missing file" in episode.digest()
        assert "FAILED" in episode.digest()


class TestPrompt:
    def test_prompt_embeds_the_episodes_and_forbids_inline_ids(self):
        episodes = loader.synthetic_episodes()
        prompt = build_prompt("run-the-tests", 1, ["Run pytest."], episodes)
        assert "ep-001" in prompt
        assert "Never write an episode id inside the step text" in prompt
        assert "run_script" in prompt

    def test_schema_requires_citations_per_step(self):
        assert "episodes" in InducedStep.model_fields
        assert InducedSkill.model_fields["steps"].annotation.__args__[0] is InducedStep
