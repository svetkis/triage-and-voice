from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.models import ExtractedEntities, TriageResult
from src.triage import TriageFailure, run_triage


def _make_parsed_completion(parsed: TriageResult | None, finish_reason: str = "stop") -> SimpleNamespace:
    """Build a fake ParsedChatCompletion matching the shape openai SDK returns from .parse()."""
    message = SimpleNamespace(parsed=parsed, role="assistant")
    choice = SimpleNamespace(message=message, index=0, finish_reason=finish_reason)
    return SimpleNamespace(id="fake", choices=[choice])


def _mock_client(completion: SimpleNamespace) -> AsyncMock:
    client = AsyncMock()
    client.beta.chat.completions.parse = AsyncMock(return_value=completion)
    return client


VALID_TRIAGE = TriageResult(
    category="order_status",
    urgency="medium",
    requested_data=["order_status"],
    extracted_entities=ExtractedEntities(order_id="ORD-123", product_id=None),
    user_emotional_state="neutral",
)


@patch("src.triage._get_client")
async def test_parsed_triage_result_is_returned(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client(_make_parsed_completion(VALID_TRIAGE))

    result = await run_triage("Where is my order ORD-123?", history=[], prompt="SYSTEM PROMPT")

    assert isinstance(result, TriageResult)
    assert result.category == "order_status"
    assert result.urgency == "medium"
    assert result.extracted_entities.order_id == "ORD-123"


@patch("src.triage._get_client")
async def test_none_parsed_raises_triage_failure(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client(
        _make_parsed_completion(None, finish_reason="content_filter")
    )

    with pytest.raises(TriageFailure):
        await run_triage("hello", history=[], prompt="SYSTEM PROMPT")


@patch("src.triage._get_client")
async def test_prompt_is_passed_as_system_message(mock_get_client: AsyncMock):
    """The prompt argument must be forwarded to the LLM as the system message."""
    client = _mock_client(_make_parsed_completion(VALID_TRIAGE))
    mock_get_client.return_value = client

    await run_triage("hi", history=[], prompt="CUSTOM VERTICAL PROMPT")

    call_kwargs = client.beta.chat.completions.parse.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "CUSTOM VERTICAL PROMPT"}
