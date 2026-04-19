"""Tests for domain models."""

import pytest
from pydantic import ValidationError

from src.models import (
    BotResponse,
    ChatMessage,
    ExtractedEntities,
    TriageResult,
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

    def test_invalid_urgency_raises(self):
        with pytest.raises(ValidationError):
            TriageResult(category="complaint", urgency="extreme")

    def test_defaults(self):
        result = TriageResult(category="complaint", urgency="low")
        assert result.requested_data == []
        assert result.extracted_entities.order_id is None
        assert result.extracted_entities.product_id is None
        assert result.user_emotional_state == "neutral"


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
