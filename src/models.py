"""Shared pydantic models — pattern + transport types (TriageResult, ChatMessage, BotResponse)."""

from typing import Literal

from pydantic import BaseModel, Field

# Type aliases for readability
Intent = str
Category = str
Urgency = Literal["low", "medium", "high", "critical"]
EmotionalState = Literal["neutral", "frustrated", "angry", "distressed"]
HarmState = Literal["none", "past", "acute", "unclear"]


class ExtractedEntities(BaseModel):
    order_id: str | None = None
    product_id: str | None = None


class TriageClassification(BaseModel):
    """Raw output of the triage LLM — independent axes (intent, emotional_state, harm_state).

    The LLM does NOT fuse these axes into a single category. Fusion is the job
    of a domain-specific resolver between triage and gate, which lets the fusion
    rule (including safe-defaults) be covered by deterministic unit tests.
    """

    intent: Intent
    urgency: Urgency
    requested_data: list[str] = Field(default_factory=list)
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    user_emotional_state: EmotionalState = "neutral"
    harm_state: HarmState = "none"


class TriageResult(BaseModel):
    """Gate input — `category` is produced by a resolver from a TriageClassification."""

    category: Category
    urgency: Urgency
    requested_data: list[str] = Field(default_factory=list)
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    user_emotional_state: EmotionalState = "neutral"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class BotResponse(BaseModel):
    """Pipeline output. `classification` carries the triage axes that drove this
    response.

    For pipelines that run triage: `None` iff triage did not return successfully
    (failed before producing a classification); populated on every post-triage
    outcome, including fallbacks after voice or gate failures. This is what lets
    eval harnesses tell triage-layer failures apart from post-triage failures.

    For bots that do not invoke triage (e.g. the naive baseline), `classification`
    is always `None` — absence of triage, not triage failure. Consumers that care
    about this distinction should key off the endpoint, not the field."""

    text: str
    human_handoff: bool = False
    trace: list[str] = Field(default_factory=list)
    classification: TriageClassification | None = None
