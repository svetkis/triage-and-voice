"""Voice module — generates user-facing responses using persona prompts with injected verified data."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from openai import AsyncOpenAI

from src.config import get_settings
from src.models import ChatMessage, GateDecision

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "voice"


def _get_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


def _render_prompt(persona: str, injected_data: dict[str, str]) -> str:
    """Load and render a Jinja2 persona prompt template."""
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)), keep_trailing_newline=True)
    template = env.get_template(f"{persona}.md")
    return template.render(injected_data=injected_data)


async def generate_response(
    gate_decision: GateDecision,
    user_message: str,
    history: list[ChatMessage],
) -> str:
    """Generate a user-facing response using the persona prompt and injected data."""
    client = _get_client()
    settings = get_settings()

    system_prompt = _render_prompt(gate_decision.voice_persona, gate_decision.injected_data)

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.model,
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content
