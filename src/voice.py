"""Voice module — generates user-facing responses from a persona template + injected data."""

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template
from openai import AsyncOpenAI

from src.config import get_settings
from src.gate.decision import VoiceCallSpec
from src.models import ChatMessage


class VoiceFailure(Exception):
    """Raised when the voice LLM returns no usable content (e.g. content-filter block)."""


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
def _get_template(path_str: str) -> Template:
    path = Path(path_str)
    env = Environment(loader=FileSystemLoader(str(path.parent)), keep_trailing_newline=True)
    return env.get_template(path.name)


def _render_prompt_from_path(path_str: str, injected_data: dict[str, str]) -> str:
    """Load and render a Jinja2 persona prompt template from an explicit path."""
    return _get_template(path_str).render(injected_data=injected_data)


async def generate_response(
    voice_call: VoiceCallSpec,
    payload: dict[str, str],
    persona_template_path: str,
    user_message: str,
    history: list[ChatMessage],
) -> str:
    """Generate a user-facing response using the persona prompt and injected data."""
    client = _get_client()
    settings = get_settings()

    # Only keys the voice_call explicitly asked for are passed to the LLM.
    injected_for_llm = {k: payload[k] for k in voice_call.inject_data_keys if k in payload}
    system_prompt = _render_prompt_from_path(persona_template_path, injected_for_llm)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=0.7,
        seed=settings.llm_seed,
    )
    content = response.choices[0].message.content
    if content is None:
        raise VoiceFailure(
            f"Voice LLM returned no content (finish_reason={response.choices[0].finish_reason!r}); "
            "likely content-filter block."
        )
    return content
