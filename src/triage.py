"""Triage classifier — calls LLM in JSON mode, validates into a TriageResult.

Uses plain JSON mode rather than OpenAI-specific structured outputs, so the
same code runs against any OpenAI-compatible endpoint (DeepSeek, OpenRouter,
local Ollama). The vertical's triage prompt must instruct the model to emit
a valid JSON object matching `TriageResult`.
"""

from functools import lru_cache

from openai import AsyncOpenAI
from pydantic import ValidationError

from src.config import get_settings
from src.models import ChatMessage, TriageResult


class TriageFailure(Exception):
    """Raised when the triage LLM returns no content or malformed JSON."""


@lru_cache
def _get_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )


async def run_triage(user_message: str, history: list[ChatMessage], prompt: str) -> TriageResult:
    """Classify a user message via LLM in JSON mode.

    `prompt` is the system prompt for the triage call — supplied by the caller
    (typically loaded once at Pipeline construction from the vertical's prompt file).
    """
    client = _get_client()
    settings = get_settings()

    messages: list[dict] = [{"role": "system", "content": prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.0,
        seed=settings.llm_seed,
    )
    content = response.choices[0].message.content
    if content is None:
        raise TriageFailure(
            "Triage LLM returned no content "
            f"(finish_reason={response.choices[0].finish_reason!r})."
        )
    try:
        return TriageResult.model_validate_json(content)
    except ValidationError as e:
        raise TriageFailure(f"Triage returned malformed JSON: {e}") from e
