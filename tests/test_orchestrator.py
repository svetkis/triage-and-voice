"""Tests for the orchestrator pipeline."""

from unittest.mock import AsyncMock, patch

import pytest

import src.orchestrator as orchestrator_module
from src.gate.decision import GateDecision, VoiceCallSpec
from src.models import BotResponse, ChatMessage, TriageResult
from src.orchestrator import process_message
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


@pytest.fixture
def history() -> list[ChatMessage]:
    return [ChatMessage(role="user", content="Hi")]


async def test_full_pipeline_returns_correct_bot_response(history: list[ChatMessage]):
    """Full pipeline: triage → gate → voice produces correct BotResponse."""
    triage_result = _make_triage_result()
    gate_decision = _make_gate_decision()

    with (
        patch("src.orchestrator.run_triage", new_callable=AsyncMock, return_value=triage_result),
        patch.object(orchestrator_module._gate, "decide", return_value=gate_decision),
        patch("src.orchestrator.generate_response", new_callable=AsyncMock, return_value="Here's the answer!"),
    ):
        result = await process_message("What color is it?", history)

    assert isinstance(result, BotResponse)
    assert result.text == "Here's the answer!"
    assert result.human_handoff is False
    assert "triage: category=product_question, urgency=low" in result.trace
    assert "voice_response: persona='default_friendly'" in result.trace
    assert "voice: persona=default_friendly" in result.trace


async def test_triage_failure_returns_fallback_with_human_handoff(history: list[ChatMessage]):
    """When triage raises TriageFailure, return fallback BotResponse with human_handoff=True."""
    with patch("src.orchestrator.run_triage", new_callable=AsyncMock, side_effect=TriageFailure("LLM down")):
        result = await process_message("Help me", history)

    assert result.human_handoff is True
    assert "human agent" in result.text.lower()
    assert any("error" in t.lower() or "triage" in t.lower() for t in result.trace)


async def test_unexpected_exception_returns_fallback(history: list[ChatMessage]):
    """When triage raises an unexpected Exception, return fallback BotResponse."""
    with patch("src.orchestrator.run_triage", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
        result = await process_message("Help me", history)

    assert result.human_handoff is True
    assert "human agent" in result.text.lower()


async def test_voice_failure_returns_fallback_with_human_handoff(history: list[ChatMessage]):
    """When voice raises VoiceFailure (e.g. content-filter), return fallback with human_handoff=True."""
    triage_result = _make_triage_result()
    gate_decision = _make_gate_decision()

    with (
        patch("src.orchestrator.run_triage", new_callable=AsyncMock, return_value=triage_result),
        patch.object(orchestrator_module._gate, "decide", return_value=gate_decision),
        patch(
            "src.orchestrator.generate_response",
            new_callable=AsyncMock,
            side_effect=VoiceFailure("content filtered"),
        ),
    ):
        result = await process_message("Help me", history)

    assert result.human_handoff is True
    assert "human agent" in result.text.lower()
    assert any("voice" in t.lower() for t in result.trace)


async def test_trace_includes_gate_reasoning(history: list[ChatMessage]):
    """Trace should include all gate reasoning entries."""
    triage_result = _make_triage_result(category="refund_request", urgency="medium", requested_data=["refund_policy"])
    gate_decision = _make_gate_decision(
        reasoning_trace=["voice_response: persona='default_friendly'", "inject_data: policies→refund_policy"],
    )

    with (
        patch("src.orchestrator.run_triage", new_callable=AsyncMock, return_value=triage_result),
        patch.object(orchestrator_module._gate, "decide", return_value=gate_decision),
        patch("src.orchestrator.generate_response", new_callable=AsyncMock, return_value="Policy info here."),
    ):
        result = await process_message("I want a refund", history)

    assert "inject_data: policies→refund_policy" in result.trace
