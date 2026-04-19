"""Triage classifier — calls LLM with structured outputs, returns a parsed TriageResult."""

from functools import lru_cache

from openai import AsyncOpenAI

from src.config import get_settings
from src.models import ChatMessage, TriageResult


class TriageFailure(Exception):
    """Raised when the triage LLM returns no parsed content (e.g. content-filter block)."""


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
    """Classify a user message via LLM using structured outputs.

    `prompt` is the system prompt for the triage call — supplied by the caller
    (typically loaded once at Pipeline construction from the vertical's prompt file).
    """
    client = _get_client()
    settings = get_settings()

    messages: list[dict] = [{"role": "system", "content": prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    response = await client.beta.chat.completions.parse(
        model=settings.model,
        messages=messages,
        response_format=TriageResult,
        temperature=0.0,
        seed=settings.llm_seed,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise TriageFailure(
            "Triage LLM returned no parsed content "
            f"(finish_reason={response.choices[0].finish_reason!r})."
        )
    return parsed
