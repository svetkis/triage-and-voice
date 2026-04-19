from src.gate.actions.voice_response import VoiceResponseAction
from src.gate.decision import GateDecision
from src.models import ExtractedEntities, TriageResult


def _triage():
    return TriageResult(
        category="product_question", urgency="medium",
        requested_data=[], extracted_entities=ExtractedEntities(),
        user_emotional_state="neutral",
    )


def test_sets_voice_call_with_persona():
    decision = GateDecision()
    VoiceResponseAction().apply(
        _triage(), decision,
        {"persona": "empathetic", "inject_data": ["hotline"]},
    )
    assert decision.voice_call is not None
    assert decision.voice_call.persona == "empathetic"
    assert decision.voice_call.inject_data_keys == ["hotline"]


def test_no_inject_data_defaults_empty_list():
    decision = GateDecision()
    VoiceResponseAction().apply(_triage(), decision, {"persona": "plain"})
    assert decision.voice_call.inject_data_keys == []
