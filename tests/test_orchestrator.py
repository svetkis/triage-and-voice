"""Tests for the orchestrator Pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.gate.decision import GateDecision, VoiceCallSpec
from src.models import BotResponse, ChatMessage, TriageResult
from src.orchestrator import Pipeline
from src.triage import TriageFailure
from src.voice import VoiceFailure


def _make_triage_result(**overrides) -> TriageResult:
    defaults = {"category": "product_question", "urgency": "low"}
    defaults.update(overrides)
    return TriageResult(**defaults)


def _make_gate_decision(**overrides) -> GateDecision:
    defaults = {
        "handoff": False,
        "payload": {},
        "voice_call": VoiceCallSpec(persona="default_friendly", inject_data_keys=[]),
        "reasoning_trace": ["voice_response: persona='default_friendly'"],
    }
    defaults.update(overrides)
    return GateDecision(**defaults)


def _make_pipeline(gate_decision: GateDecision | None = None) -> tuple[Pipeline, MagicMock]:
    """Build a Pipeline with a mock Gate. Returns (pipeline, mock_gate)."""
    mock_gate = MagicMock()
    if gate_decision is not None:
        mock_gate.decide.return_value = gate_decision
    mock_gate.persona_template_path.return_value = "prompts/voice/default_friendly.md"
    return Pipeline(gate=mock_gate, triage_prompt="TRIAGE PROMPT"), mock_gate


@pytest.fixture
def history() -> list[ChatMessage]:
    return [ChatMessage(role="user", content="Hi")]


async def test_full_pipeline_returns_correct_bot_response(history: list[ChatMessage]):
    """Full pipeline: triage → gate → voice produces correct BotResponse."""
    triage_result = _make_triage_result()
    gate_decision = _make_gate_decision()
    pipeline, _ = _make_pipeline(gate_decision)

    with (
        patch("src.orchestrator.run_triage", new_callable=AsyncMock, return_value=triage_result),
        patch("src.orchestrator.generate_response", new_callable=AsyncMock, return_value="Here's the answer!"),
    ):
        result = await pipeline.process_message("What color is it?", history)

    assert isinstance(result, BotResponse)
    assert result.text == "Here's the answer!"
    assert result.human_handoff is False
    assert "triage: category=product_question, urgency=low" in result.trace
    assert "voice_response: persona='default_friendly'" in result.trace
    assert "voice: persona=default_friendly" in result.trace


async def test_triage_failure_returns_fallback_with_human_handoff(history: list[ChatMessage]):
    """When triage raises TriageFailure, return fallback BotResponse with human_handoff=True."""
    pipeline, _ = _make_pipeline()

    with patch("src.orchestrator.run_triage", new_callable=AsyncMock, side_effect=TriageFailure("LLM down")):
        result = await pipeline.process_message("Help me", history)

    assert result.human_handoff is True
    assert "human agent" in result.text.lower()
    assert any("error" in t.lower() or "triage" in t.lower() for t in result.trace)


async def test_unexpected_exception_returns_fallback(history: list[ChatMessage]):
    """When triage raises an unexpected Exception, return fallback BotResponse."""
    pipeline, _ = _make_pipeline()

    with patch("src.orchestrator.run_triage", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
        result = await pipeline.process_message("Help me", history)

    assert result.human_handoff is True
    assert "human agent" in result.text.lower()


async def test_voice_failure_returns_fallback_with_human_handoff(history: list[ChatMessage]):
    """When voice raises VoiceFailure (e.g. content-filter), return fallback with human_handoff=True."""
    triage_result = _make_triage_result()
    gate_decision = _make_gate_decision()
    pipeline, _ = _make_pipeline(gate_decision)

    with (
        patch("src.orchestrator.run_triage", new_callable=AsyncMock, return_value=triage_result),
        patch(
            "src.orchestrator.generate_response",
            new_callable=AsyncMock,
            side_effect=VoiceFailure("content filtered"),
        ),
    ):
        result = await pipeline.process_message("Help me", history)

    assert result.human_handoff is True
    assert "human agent" in result.text.lower()
    assert any("voice" in t.lower() for t in result.trace)


async def test_trace_includes_gate_reasoning(history: list[ChatMessage]):
    """Trace should include all gate reasoning entries."""
    triage_result = _make_triage_result(category="refund_request", urgency="medium", requested_data=["refund_policy"])
    gate_decision = _make_gate_decision(
        reasoning_trace=["voice_response: persona='default_friendly'", "inject_data: policies→refund_policy"],
    )
    pipeline, _ = _make_pipeline(gate_decision)

    with (
        patch("src.orchestrator.run_triage", new_callable=AsyncMock, return_value=triage_result),
        patch("src.orchestrator.generate_response", new_callable=AsyncMock, return_value="Policy info here."),
    ):
        result = await pipeline.process_message("I want a refund", history)

    assert "inject_data: policies→refund_policy" in result.trace


async def test_pipeline_forwards_its_triage_prompt_to_run_triage(history: list[ChatMessage]):
    """Pipeline must pass its own triage_prompt into run_triage — proves per-vertical parameterization."""
    pipeline = Pipeline(gate=MagicMock(), triage_prompt="VERTICAL-SPECIFIC PROMPT")
    pipeline._gate.decide.return_value = _make_gate_decision(voice_call=None, payload={"info": "ok"})

    with patch(
        "src.orchestrator.run_triage",
        new_callable=AsyncMock,
        return_value=_make_triage_result(),
    ) as mock_triage:
        await pipeline.process_message("hi", history)

    assert mock_triage.call_args.kwargs.get("prompt") == "VERTICAL-SPECIFIC PROMPT" or (
        len(mock_triage.call_args.args) >= 3 and mock_triage.call_args.args[2] == "VERTICAL-SPECIFIC PROMPT"
    )
