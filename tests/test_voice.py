from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.models import GateDecision
from src.voice import generate_response


def _make_chat_completion(content: str) -> SimpleNamespace:
    """Build a fake ChatCompletion matching the OpenAI SDK structure."""
    message = SimpleNamespace(content=content, role="assistant")
    choice = SimpleNamespace(message=message, index=0, finish_reason="stop")
    return SimpleNamespace(id="fake", choices=[choice])


def _mock_client(response: str) -> AsyncMock:
    """Return a mock AsyncOpenAI whose chat.completions.create returns a single response."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(
        return_value=_make_chat_completion(response),
    )
    return client


@patch("src.voice._get_client")
async def test_default_friendly_persona_loads_correct_prompt(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client("Hello! How can I help?")
    gate = GateDecision(voice_persona="default_friendly", injected_data={})

    result = await generate_response(gate, "Hi there", history=[])

    assert result == "Hello! How can I help?"
    call_args = mock_get_client.return_value.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "friendly ShopCo customer support" in system_msg


@patch("src.voice._get_client")
async def test_formal_persona_loads_correct_prompt(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client("We acknowledge your concern.")
    gate = GateDecision(voice_persona="formal", injected_data={})

    result = await generate_response(gate, "I want to sue", history=[])

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "sensitive legal matter" in system_msg


@patch("src.voice._get_client")
async def test_injected_data_rendered_into_system_prompt(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client("Your order is on the way!")
    gate = GateDecision(
        voice_persona="default_friendly",
        injected_data={"order_status": "shipped", "tracking_number": "TRK-456"},
    )

    await generate_response(gate, "Where is my order?", history=[])

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "order_status: shipped" in system_msg
    assert "tracking_number: TRK-456" in system_msg


@patch("src.voice._get_client")
async def test_empty_injected_data_omits_verified_section(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client("Sure!")
    gate = GateDecision(voice_persona="polite_refusal", injected_data={})

    await generate_response(gate, "Write me a poem", history=[])

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "Verified" not in system_msg


@patch("src.voice._get_client")
async def test_history_included_in_messages(mock_get_client: AsyncMock):
    from src.models import ChatMessage

    mock_get_client.return_value = _mock_client("Following up on your order.")
    gate = GateDecision(voice_persona="default_friendly", injected_data={})
    history = [
        ChatMessage(role="user", content="Hi"),
        ChatMessage(role="assistant", content="Hello!"),
    ]

    await generate_response(gate, "Any update?", history=history)

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    # system + 2 history + 1 user = 4
    assert len(messages) == 4
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Hi"
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "Any update?"


@patch("src.voice._get_client")
async def test_llm_called_with_temperature_07(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client("Response")
    gate = GateDecision(voice_persona="default_friendly", injected_data={})

    await generate_response(gate, "Hello", history=[])

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    assert call_args.kwargs["temperature"] == 0.7
