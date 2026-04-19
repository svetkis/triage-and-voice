"""Naive single-prompt bot — baseline for comparison with triage-and-voice."""

from functools import lru_cache
from pathlib import Path

from openai import AsyncOpenAI

from src.config import get_settings
from src.models import BotResponse, ChatMessage

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "naive" / "bot.md"


@lru_cache
def _get_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


@lru_cache
def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


async def process_message(user_message: str, history: list[ChatMessage]) -> BotResponse:
    """Single LLM call with system prompt + history + user message. No data injection."""
    client = _get_client()
    settings = get_settings()

    messages: list[dict[str, str]] = [{"role": "system", "content": _load_prompt()}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=0.7,
        seed=settings.llm_seed,
    )

    text = response.choices[0].message.content or ""
    return BotResponse(
        text=text,
        human_handoff=False,
        trace=["naive: single-prompt, no gate"],
    )
