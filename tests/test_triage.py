import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.models import TriageResult
from src.triage import TriageFailure, run_triage


def _make_chat_completion(content: str) -> SimpleNamespace:
    """Build a fake ChatCompletion matching the OpenAI SDK structure."""
    message = SimpleNamespace(content=content, role="assistant")
    choice = SimpleNamespace(message=message, index=0, finish_reason="stop")
    return SimpleNamespace(id="fake", choices=[choice])


def _mock_client(responses: list[str]) -> AsyncMock:
    """Return a mock AsyncOpenAI whose chat.completions.create returns *responses* in order."""
    client = AsyncMock()
    side_effects = [_make_chat_completion(r) for r in responses]
    client.chat.completions.create = AsyncMock(side_effect=side_effects)
    return client


VALID_JSON = json.dumps(
    {
        "category": "order_status",
        "urgency": "medium",
        "requested_data": ["order_status"],
        "extracted_entities": {"order_id": "ORD-123", "product_id": None},
        "user_emotional_state": "neutral",
    }
)


@patch("src.triage._get_client")
async def test_valid_json_parsed_into_triage_result(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client([VALID_JSON])

    result = await run_triage("Where is my order ORD-123?", history=[])

    assert isinstance(result, TriageResult)
    assert result.category == "order_status"
    assert result.urgency == "medium"
    assert result.extracted_entities.order_id == "ORD-123"
    assert "order_status" in result.requested_data


@patch("src.triage._get_client")
async def test_invalid_json_retries_then_succeeds(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client(["NOT JSON AT ALL", VALID_JSON])

    result = await run_triage("Where is my order ORD-123?", history=[])

    assert isinstance(result, TriageResult)
    assert result.category == "order_status"
    # Two calls: original + retry
    assert mock_get_client.return_value.chat.completions.create.call_count == 2


@patch("src.triage._get_client")
async def test_two_invalid_jsons_raises_triage_failure(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client(["BAD", "ALSO BAD"])

    with pytest.raises(TriageFailure):
        await run_triage("hello", history=[])
