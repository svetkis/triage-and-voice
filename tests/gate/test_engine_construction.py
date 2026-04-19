from pathlib import Path

from src.gate.engine import Gate

FIXTURE = Path(__file__).parent / "fixtures" / "minimal.yaml"


def test_from_yaml_registers_builtin_actions():
    gate = Gate.from_yaml(FIXTURE)
    assert "voice_response" in gate._actions
    assert "handoff" in gate._actions
    assert "inject_data" in gate._actions


def test_register_source_adds_to_registry():
    gate = Gate.from_yaml(FIXTURE)

    class FakeSrc:
        def fetch(self, params): return "ok"

    gate.register_source("stub", FakeSrc())
    assert "stub" in gate._sources


def test_register_action_adds_to_registry():
    gate = Gate.from_yaml(FIXTURE)

    class FakeAction:
        def apply(self, triage, decision, params): ...

    gate.register_action("custom", FakeAction())
    assert "custom" in gate._actions
