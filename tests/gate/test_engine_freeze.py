from pathlib import Path

import pytest

from src.gate.engine import Gate
from src.models import ExtractedEntities, TriageResult


FIXTURES = Path(__file__).parent / "fixtures"


def _triage(category: str, urgency: str = "medium") -> TriageResult:
    return TriageResult(
        category=category, urgency=urgency,
        requested_data=[], extracted_entities=ExtractedEntities(),
        user_emotional_state="neutral",
    )


def test_freeze_with_unknown_action_type_raises():
    gate = Gate.from_yaml(FIXTURES / "unknown_action_type.yaml")
    with pytest.raises(ValueError, match=r"unknown action type 'voice_responce'.*categories\.refund\.actions\[1\]"):
        gate.freeze()


def test_freeze_with_unknown_persona_raises():
    gate = Gate.from_yaml(FIXTURES / "unknown_persona.yaml")
    with pytest.raises(ValueError, match=r"unknown persona 'formall'"):
        gate.freeze()


def test_freeze_with_unknown_source_raises_after_registration_phase():
    gate = Gate.from_yaml(FIXTURES / "multi_action.yaml")
    with pytest.raises(ValueError, match=r"unknown source 'hotline'"):
        gate.freeze()


def test_decide_auto_freezes():
    gate = Gate.from_yaml(FIXTURES / "multi_action.yaml")

    class _StaticSrc:
        def fetch(self, params): return "ok"

    gate.register_source("hotline", _StaticSrc())
    decision = gate.decide(_triage(category="emergency"))
    assert gate._frozen is True
    assert decision.handoff is True


def test_register_after_freeze_raises():
    gate = Gate.from_yaml(FIXTURES / "multi_action.yaml")

    class _StaticSrc:
        def fetch(self, params): return "ok"

    gate.register_source("hotline", _StaticSrc())
    gate.freeze()

    with pytest.raises(RuntimeError, match=r"frozen"):
        gate.register_source("another", _StaticSrc())

    with pytest.raises(RuntimeError, match=r"frozen"):
        gate.register_action("custom", object())


def test_freeze_is_idempotent():
    gate = Gate.from_yaml(FIXTURES / "multi_action.yaml")

    class _StaticSrc:
        def fetch(self, params): return "ok"

    gate.register_source("hotline", _StaticSrc())
    gate.freeze()
    gate.freeze()
    assert gate._frozen is True
