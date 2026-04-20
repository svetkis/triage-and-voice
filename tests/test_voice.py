from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.gate.decision import VoiceCallSpec
from src.voice import VoiceFailure, generate_response

_PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "shopco"
    / "prompts"
    / "voice"
)


def _persona_path(persona: str) -> str:
    return str(_PROMPTS_DIR / f"{persona}.md")


def _make_chat_completion(content: str | None, finish_reason: str = "stop") -> SimpleNamespace:
    """Build a fake ChatCompletion matching the OpenAI SDK structure."""
    message = SimpleNamespace(content=content, role="assistant")
    choice = SimpleNamespace(message=message, index=0, finish_reason=finish_reason)
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
    voice_call = VoiceCallSpec(persona="default_friendly", inject_data_keys=[])

    result = await generate_response(
        voice_call,
        payload={},
        persona_template_path=_persona_path("default_friendly"),
        user_message="Hi there",
        history=[],
    )

    assert result == "Hello! How can I help?"
    call_args = mock_get_client.return_value.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "friendly ShopCo customer support" in system_msg


@patch("src.voice._get_client")
async def test_formal_persona_loads_correct_prompt(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client("We acknowledge your concern.")
    voice_call = VoiceCallSpec(persona="formal", inject_data_keys=[])

    await generate_response(
        voice_call,
        payload={},
        persona_template_path=_persona_path("formal"),
        user_message="I want to sue",
        history=[],
    )

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "sensitive legal matter" in system_msg


@patch("src.voice._get_client")
async def test_injected_data_rendered_into_system_prompt(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client("Your order is on the way!")
    voice_call = VoiceCallSpec(
        persona="default_friendly",
        inject_data_keys=["order_status", "tracking_number"],
    )
    payload = {"order_status": "shipped", "tracking_number": "TRK-456"}

    await generate_response(
        voice_call,
        payload=payload,
        persona_template_path=_persona_path("default_friendly"),
        user_message="Where is my order?",
        history=[],
    )

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "order_status: shipped" in system_msg
    assert "tracking_number: TRK-456" in system_msg


@patch("src.voice._get_client")
async def test_empty_injected_data_omits_verified_section(mock_get_client: AsyncMock):
    mock_get_client.return_value = _mock_client("Sure!")
    voice_call = VoiceCallSpec(persona="polite_refusal", inject_data_keys=[])

    await generate_response(
        voice_call,
        payload={},
        persona_template_path=_persona_path("polite_refusal"),
        user_message="Write me a poem",
        history=[],
    )

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "Verified" not in system_msg


@patch("src.voice._get_client")
async def test_history_included_in_messages(mock_get_client: AsyncMock):
    from src.models import ChatMessage

    mock_get_client.return_value = _mock_client("Following up on your order.")
    voice_call = VoiceCallSpec(persona="default_friendly", inject_data_keys=[])
    history = [
        ChatMessage(role="user", content="Hi"),
        ChatMessage(role="assistant", content="Hello!"),
    ]

    await generate_response(
        voice_call,
        payload={},
        persona_template_path=_persona_path("default_friendly"),
        user_message="Any update?",
        history=history,
    )

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
    voice_call = VoiceCallSpec(persona="default_friendly", inject_data_keys=[])

    await generate_response(
        voice_call,
        payload={},
        persona_template_path=_persona_path("default_friendly"),
        user_message="Hello",
        history=[],
    )

    call_args = mock_get_client.return_value.chat.completions.create.call_args
    assert call_args.kwargs["temperature"] == 0.7


@patch("src.voice._get_client")
async def test_none_content_raises_voice_failure(mock_get_client: AsyncMock):
    """Content-filter / safety refusal returns content=None — must raise VoiceFailure, not pass empty string."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(
        return_value=_make_chat_completion(None, finish_reason="content_filter"),
    )
    mock_get_client.return_value = client
    voice_call = VoiceCallSpec(persona="default_friendly", inject_data_keys=[])

    with pytest.raises(VoiceFailure, match="content_filter"):
        await generate_response(
            voice_call,
            payload={},
            persona_template_path=_persona_path("default_friendly"),
            user_message="Something forbidden",
            history=[],
        )
