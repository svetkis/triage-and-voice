import pytest

from src.gate.actions.inject_data import InjectDataAction
from src.gate.decision import GateDecision
from src.models import ExtractedEntities, TriageResult


class StubSource:
    def __init__(self, value: str | None):
        self.value = value
        self.last_params: dict | None = None

    def fetch(self, params: dict) -> str | None:
        self.last_params = params
        return self.value


def _triage():
    return TriageResult(
        category="product_question", urgency="medium",
        requested_data=[], extracted_entities=ExtractedEntities(),
        user_emotional_state="neutral",
    )


def test_injects_value_under_key():
    src = StubSource("hello world")
    action = InjectDataAction({"stub": src})
    decision = GateDecision()

    action.apply(_triage(), decision, {"source": "stub", "key": "greeting"})

    assert decision.payload["greeting"] == "hello world"


def test_none_value_is_not_written():
    action = InjectDataAction({"stub": StubSource(None)})
    decision = GateDecision()

    action.apply(_triage(), decision, {"source": "stub", "key": "missing"})

    assert "missing" not in decision.payload


def test_unknown_source_raises():
    action = InjectDataAction({})
    with pytest.raises(KeyError):
        action.apply(_triage(), GateDecision(), {"source": "nope", "key": "x"})


def test_extracted_entities_are_passed_to_source():
    captured = {}

    class Capture:
        def fetch(self, params):
            captured.update(params)
            return "ok"

    action = InjectDataAction({"cap": Capture()})
    triage = TriageResult(
        category="product_question", urgency="medium",
        requested_data=[],
        extracted_entities=ExtractedEntities(order_id="ORD-42"),
        user_emotional_state="neutral",
    )
    action.apply(triage, GateDecision(), {"source": "cap", "key": "x"})

    assert captured.get("order_id") == "ORD-42"


def test_explicit_yaml_params_override_entities():
    captured = {}

    class Capture:
        def fetch(self, params):
            captured.update(params)
            return "ok"

    action = InjectDataAction({"cap": Capture()})
    triage = TriageResult(
        category="product_question", urgency="medium",
        requested_data=[],
        extracted_entities=ExtractedEntities(order_id="ORD-42"),
        user_emotional_state="neutral",
    )
    action.apply(triage, GateDecision(), {"source": "cap", "key": "x", "order_id": "OVERRIDE"})
    assert captured["order_id"] == "OVERRIDE"
