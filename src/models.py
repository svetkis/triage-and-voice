"""Domain models for the Triage-and-Voice pattern."""

from typing import Literal

from pydantic import BaseModel

# Type aliases for readability
Category = Literal[
    "order_status",
    "refund_request",
    "product_question",
    "complaint",
    "legal_threat",
    "safety_issue",
    "out_of_scope",
]
Urgency = Literal["low", "medium", "high", "critical"]
EmotionalState = Literal["neutral", "frustrated", "angry", "distressed"]
VoicePersona = Literal[
    "default_friendly", "formal", "empathetic_escalation", "polite_refusal"
]


class ExtractedEntities(BaseModel):
    order_id: str | None = None
    product_id: str | None = None


class TriageResult(BaseModel):
    """Triage classifier output."""

    category: Category
    urgency: Urgency
    requested_data: list[str] = []
    extracted_entities: ExtractedEntities = ExtractedEntities()
    user_emotional_state: EmotionalState = "neutral"


class GateDecision(BaseModel):
    """Deterministic gate output."""

    voice_persona: VoicePersona = "default_friendly"
    injected_data: dict[str, str] = {}
    human_handoff: bool = False
    reasoning_trace: list[str] = []


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class VoiceInput(BaseModel):
    persona: VoicePersona
    user_message: str
    injected_data: dict[str, str] = {}
    history: list[ChatMessage] = []


class BotResponse(BaseModel):
    text: str
    human_handoff: bool = False
    trace: list[str] = []
