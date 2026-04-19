
from src.gate.config import ActionSpec, CategoryRule, GateConfig


def test_minimal_valid_config():
    cfg = GateConfig(
        personas={"neutral": "prompts/voice/neutral.md"},
        categories={
            "greeting": CategoryRule(
                actions=[ActionSpec(type="voice_response", params={"persona": "neutral"})]
            )
        },
        default=CategoryRule(
            actions=[ActionSpec(type="voice_response", params={"persona": "neutral"})]
        ),
    )
    assert "greeting" in cfg.categories


def test_empty_overrides_default_to_empty_list():
    cfg = GateConfig(
        personas={},
        categories={},
        default=CategoryRule(actions=[]),
    )
    assert cfg.overrides.force_handoff_on_urgency == []
