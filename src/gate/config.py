"""Pydantic schema for gate YAML config."""

from pydantic import BaseModel, Field


class ActionSpec(BaseModel):
    type: str
    params: dict = Field(default_factory=dict)


class CategoryRule(BaseModel):
    actions: list[ActionSpec] = []
    stop_on_match: bool = False


class OverridesSpec(BaseModel):
    force_handoff_on_urgency: list[str] = []


class GateConfig(BaseModel):
    personas: dict[str, str] = {}
    categories: dict[str, CategoryRule] = {}
    default: CategoryRule = CategoryRule(actions=[])
    overrides: OverridesSpec = OverridesSpec()
