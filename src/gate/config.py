"""Pydantic schema for gate YAML config."""

from pathlib import Path

import yaml
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


def load_config(path: Path | str) -> GateConfig:
    """Load and validate a gate YAML config. Raises pydantic ValidationError on schema violation."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return GateConfig.model_validate(raw or {})
