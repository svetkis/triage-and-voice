"""Triage classifier — calls LLM and parses structured JSON response."""

from pathlib import Path

from openai import AsyncOpenAI

from src.config import get_settings
from src.models import ChatMessage, TriageResult

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "triage.md"

_RETRY_SUFFIX = (
    "\n\nYour previous response was not valid JSON. "
    "You MUST respond with ONLY a raw JSON object, no markdown, no explanation."
)


class TriageFailure(Exception):
    """Raised when the triage classifier fails to produce valid JSON after retries."""


def _get_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.llm_timeout_seconds,
    )


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


async def run_triage(user_message: str, history: list[ChatMessage]) -> TriageResult:
    """Classify a user message via LLM. Retries once on invalid JSON."""
    client = _get_client()
    settings = get_settings()
    system_prompt = _load_prompt()

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    # First attempt
    raw = await _call_llm(client, settings.model, messages)
    result = _try_parse(raw)
    if result is not None:
        return result

    # Retry with stricter prompt
    messages[0] = {"role": "system", "content": system_prompt + _RETRY_SUFFIX}
    raw = await _call_llm(client, settings.model, messages)
    result = _try_parse(raw)
    if result is not None:
        return result

    raise TriageFailure(f"Failed to parse triage response after retry. Last raw: {raw!r}")


async def _call_llm(client: AsyncOpenAI, model: str, messages: list[dict]) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return response.choices[0].message.content


def _try_parse(raw: str) -> TriageResult | None:
    try:
        return TriageResult.model_validate_json(raw)
    except Exception:
        return None
