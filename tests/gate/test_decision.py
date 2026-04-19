from src.gate.decision import GateDecision, VoiceCallSpec


def test_default_decision_is_noop():
    d = GateDecision()
    assert d.handoff is False
    assert d.handoff_reason is None
    assert d.payload == {}
    assert d.voice_call is None
    assert d.reasoning_trace == []


def test_voice_call_spec_requires_persona():
    spec = VoiceCallSpec(persona="neutral")
    assert spec.persona == "neutral"
    assert spec.inject_data_keys == []
