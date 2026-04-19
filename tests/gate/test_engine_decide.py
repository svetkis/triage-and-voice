from pathlib import Path

from src.gate.engine import Gate
from src.models import ExtractedEntities, TriageResult


FIXTURES = Path(__file__).parent / "fixtures"


class StaticSource:
    def __init__(self, value: str): self.value = value
    def fetch(self, params): return self.value


def _triage(category: str, urgency: str = "medium") -> TriageResult:
    return TriageResult(
        category=category, urgency=urgency,
        requested_data=[], extracted_entities=ExtractedEntities(),
        user_emotional_state="neutral",
    )


def test_decide_runs_all_actions_for_matching_category():
    gate = Gate.from_yaml(FIXTURES / "multi_action.yaml")
    gate.register_source("hotline", StaticSource("1-800-URGENT"))

    decision = gate.decide(_triage(category="emergency"))

    assert decision.handoff is True
    assert decision.handoff_reason == "urgent"
    assert decision.payload["contact_info"] == "1-800-URGENT"
    assert decision.voice_call.persona == "warm"
    assert decision.voice_call.inject_data_keys == ["contact_info"]


def test_unknown_category_falls_back_to_default():
    gate = Gate.from_yaml(FIXTURES / "with_overrides.yaml")
    decision = gate.decide(_triage(category="something_new"))
    assert decision.voice_call.persona == "warm"


def test_critical_urgency_forces_handoff_when_listed_in_overrides():
    gate = Gate.from_yaml(FIXTURES / "with_overrides.yaml")
    decision = gate.decide(_triage(category="refund", urgency="critical"))
    assert decision.handoff is True
    assert "override" in " ".join(decision.reasoning_trace).lower()


def test_non_listed_urgency_does_not_trigger_override():
    gate = Gate.from_yaml(FIXTURES / "with_overrides.yaml")
    decision = gate.decide(_triage(category="refund", urgency="medium"))
    assert decision.handoff is False
