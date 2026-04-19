"""Domain models for the Triage-and-Voice pattern."""

from typing import Literal

from pydantic import BaseModel

# Type aliases for readability
Category = str
Urgency = Literal["low", "medium", "high", "critical"]
EmotionalState = Literal["neutral", "frustrated", "angry", "distressed"]


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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class BotResponse(BaseModel):
    text: str
    human_handoff: bool = False
    trace: list[str] = []
