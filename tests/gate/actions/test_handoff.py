from src.gate.actions.handoff import HandoffAction
from src.gate.decision import GateDecision
from src.models import ExtractedEntities, TriageResult


def _triage():
    return TriageResult(
        category="product_question", urgency="medium",
        requested_data=[], extracted_entities=ExtractedEntities(),
        user_emotional_state="neutral",
    )


def test_handoff_sets_flag_and_reason():
    decision = GateDecision()
    HandoffAction().apply(_triage(), decision, {"reason": "escalate_to_human"})
    assert decision.handoff is True
    assert decision.handoff_reason == "escalate_to_human"
    assert any("handoff" in t for t in decision.reasoning_trace)
