"""Tests for domain models."""

import pytest
from pydantic import ValidationError

from src.models import (
    BotResponse,
    ChatMessage,
    ExtractedEntities,
    GateDecision,
    TriageResult,
    VoiceInput,
)


class TestTriageResult:
    def test_valid_triage_result_parses(self):
        result = TriageResult(
            category="refund_request",
            urgency="high",
            requested_data=["order_details"],
            extracted_entities=ExtractedEntities(order_id="ORD-123"),
            user_emotional_state="frustrated",
        )
        assert result.category == "refund_request"
        assert result.urgency == "high"
        assert result.requested_data == ["order_details"]
        assert result.extracted_entities.order_id == "ORD-123"
        assert result.extracted_entities.product_id is None
        assert result.user_emotional_state == "frustrated"

    def test_invalid_category_raises(self):
        with pytest.raises(ValidationError):
            TriageResult(category="unknown", urgency="low")

    def test_invalid_urgency_raises(self):
        with pytest.raises(ValidationError):
            TriageResult(category="complaint", urgency="extreme")

    def test_defaults(self):
        result = TriageResult(category="complaint", urgency="low")
        assert result.requested_data == []
        assert result.extracted_entities.order_id is None
        assert result.extracted_entities.product_id is None
        assert result.user_emotional_state == "neutral"


class TestGateDecision:
    def test_defaults(self):
        decision = GateDecision()
        assert decision.voice_persona == "default_friendly"
        assert decision.injected_data == {}
        assert decision.human_handoff is False
        assert decision.reasoning_trace == []

    def test_custom_values(self):
        decision = GateDecision(
            voice_persona="empathetic_escalation",
            injected_data={"order_status": "shipped"},
            human_handoff=True,
            reasoning_trace=["user is angry", "escalating"],
        )
        assert decision.voice_persona == "empathetic_escalation"
        assert decision.injected_data == {"order_status": "shipped"}
        assert decision.human_handoff is True
        assert len(decision.reasoning_trace) == 2

    def test_invalid_persona_raises(self):
        with pytest.raises(ValidationError):
            GateDecision(voice_persona="sarcastic")


class TestBotResponse:
    def test_contains_trace(self):
        resp = BotResponse(
            text="Your order is on the way!",
            trace=["looked up order", "composed reply"],
        )
        assert resp.text == "Your order is on the way!"
        assert resp.human_handoff is False
        assert len(resp.trace) == 2
        assert "looked up order" in resp.trace

    def test_defaults(self):
        resp = BotResponse(text="Hello")
        assert resp.human_handoff is False
        assert resp.trace == []


class TestChatMessage:
    def test_valid_roles(self):
        user_msg = ChatMessage(role="user", content="Hi")
        assert user_msg.role == "user"

        asst_msg = ChatMessage(role="assistant", content="Hello!")
        assert asst_msg.role == "assistant"

    def test_invalid_role_raises(self):
        with pytest.raises(ValidationError):
            ChatMessage(role="system", content="nope")


class TestVoiceInput:
    def test_minimal(self):
        vi = VoiceInput(persona="formal", user_message="Help me")
        assert vi.persona == "formal"
        assert vi.user_message == "Help me"
        assert vi.injected_data == {}
        assert vi.history == []

    def test_with_history(self):
        vi = VoiceInput(
            persona="default_friendly",
            user_message="What about my order?",
            history=[ChatMessage(role="user", content="Hi")],
        )
        assert len(vi.history) == 1
