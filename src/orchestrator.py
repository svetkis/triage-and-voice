"""Orchestrator — chains triage → gate → voice into a complete pipeline."""

import logging

from src.models import BotResponse, ChatMessage
from src.triage import run_triage, TriageFailure
from src.gate_legacy import apply_gate
from src.voice import generate_response, VoiceFailure

logger = logging.getLogger(__name__)

_FALLBACK_TEXT = (
    "I'm sorry, I'm having trouble processing your request. "
    "Let me connect you with a human agent."
)


async def process_message(user_message: str, history: list[ChatMessage]) -> BotResponse:
    """Process a user message through the triage → gate → voice pipeline."""
    trace: list[str] = []

    try:
        # 1. Triage
        triage_result = await run_triage(user_message, history)
        trace.append(f"triage: category={triage_result.category}, urgency={triage_result.urgency}")

        # 2. Gate
        gate_decision = apply_gate(triage_result)
        trace.extend(gate_decision.reasoning_trace)

        # 3. Voice
        response_text = await generate_response(gate_decision, user_message, history)
        trace.append(f"voice: persona={gate_decision.voice_persona}")

        return BotResponse(
            text=response_text,
            human_handoff=gate_decision.human_handoff,
            trace=trace,
        )

    except TriageFailure as exc:
        logger.warning("triage failed: %s", exc)
        trace.append(f"triage failed: {exc}")

    except VoiceFailure as exc:
        logger.warning("voice failed: %s", exc)
        trace.append(f"voice failed: {exc}")

    except Exception as exc:
        logger.exception("unexpected pipeline failure")
        trace.append(f"pipeline error: {type(exc).__name__}: {exc}")

    return BotResponse(
        text=_FALLBACK_TEXT,
        human_handoff=True,
        trace=trace,
    )
