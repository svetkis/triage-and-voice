# Gate Framework Design

**Date:** 2026-04-19
**Status:** Approved, ready for implementation planning
**Scope:** Refactor `src/gate.py` from a ShopCo-specific helper into a reusable framework with the ShopCo flow demoted to a worked example.

---

## Problem

`src/gate.py` mixes three concerns in one hand-written `if/else`:

1. Routing a triage `category` to a voice persona plus a human-handoff flag.
2. Data injection (policies, orders, escalation contacts) with validation and formatting.
3. Cross-cutting overrides (urgency → handoff).

Every rule is hardcoded to ShopCo's support-bot domain. Adding a new category, a new data source, or a new post-triage outcome means editing the engine. The repository is pitched as a reference implementation of the Triage-and-Voice pattern, but the pattern itself is not surfaced as a reusable artefact — only the ShopCo instance is.

This redesign makes the pattern the product.

## Non-Goals

- No generic workflow engine, no conditional DSL, no expression eval.
- No multi-tenant runtime — one framework binary per consumer deployment.
- No backwards compatibility with existing `GateDecision` shape or the `VoicePersona` `Literal` enum. These are ShopCo-leaking types and will change.
- No implicit defaults carried over from the current code (notably `urgency == "critical" → handoff`). Override policies are opt-in per consumer config.

## Scope

The gate becomes a **Command-pattern dispatcher**:

    TriageResult → list[GateAction] → GateDecision (accumulator)

- **`GateAction`**: an atomic post-triage operation (Strategy). Three action types ship in the core; consumers register more.
- **YAML config**: wires `category → [action_a, action_b, …]`. One declarative artefact per consumer.
- **`DataSource`**: a named source that the `inject_data` action pulls from. Consumers register concrete sources; the engine does not know about orders, policies, contacts, documents, or price lists.

The boundary: engine understands action **orchestration** and the three core action **types**. Everything domain-specific (what a contact is, how to format an order status, which personas exist) is consumer code.

## Architecture

### Core types (framework)

```python
# src/gate/contracts.py

class GateAction(Protocol):
    """One post-triage operation. Populates the decision accumulator."""
    def apply(self, triage: TriageResult,
              decision: GateDecision,
              params: dict) -> None: ...

class DataSource(Protocol):
    """Named data source referenced by inject_data actions."""
    def fetch(self, params: dict) -> str | None: ...
```

### The accumulator

`GateDecision` stops being a ShopCo-shaped record and becomes a slot-based accumulator that any action can write into:

```python
class GateDecision(BaseModel):
    handoff: bool = False
    handoff_reason: str | None = None
    payload: dict[str, str] = {}
    voice_call: VoiceCallSpec | None = None          # None → no LLM invocation
    reasoning_trace: list[str] = []

class VoiceCallSpec(BaseModel):
    persona: str                                     # arbitrary string, resolved via YAML personas map
    inject_data_keys: list[str] = []                 # which payload keys go to the LLM
```

`voice_persona: VoicePersona` (closed `Literal` enum) is removed. Personas become arbitrary strings whose prompt template paths are declared in the consumer YAML.

### Built-in action types

| `type` in YAML    | Reads from params                    | Writes to decision                    |
|-------------------|--------------------------------------|---------------------------------------|
| `handoff`         | `reason`                             | `handoff`, `handoff_reason`           |
| `inject_data`     | `source`, `key`, source-specific params | `payload[key]`                     |
| `voice_response`  | `persona`, optional `inject_data`    | `voice_call`                          |

That is the entire framework action surface.

### YAML schema

```yaml
# Persona registry: arbitrary string → prompt template path
personas:
  default_friendly:      prompts/voice/default_friendly.md
  formal:                prompts/voice/formal.md
  empathetic_escalation: prompts/voice/empathetic_escalation.md
  polite_refusal:        prompts/voice/polite_refusal.md

# Category → ordered list of actions
categories:

  safety_issue:
    stop_on_match: true
    actions:
      - type: handoff
        reason: safety_incident
      - type: inject_data
        source: escalation_contacts
        key: safety_hotline
        contact_key: safety_hotline
      - type: voice_response
        persona: empathetic_escalation
        inject_data: [safety_hotline]

  # ... other categories

# Fallback when no category matches
default:
  actions:
    - type: voice_response
      persona: default_friendly

# Optional — empty by default. No framework-level implicit overrides.
overrides:
  force_handoff_on_urgency: []          # e.g. [critical] to opt into the old behaviour
```

Schema is validated on config load via a pydantic model. Unknown action `type`, unknown persona reference, unknown `source` — all fail loudly at startup.

### Consumer API

```python
# examples/shopco/main.py

from gate import Gate
from .sources import OrderSource, PolicySource, ContactsSource

gate = Gate.from_yaml("examples/shopco/config/shopco.yaml")
gate.register_source("orders",               OrderSource())
gate.register_source("policies",             PolicySource())
gate.register_source("escalation_contacts",  ContactsSource())

# gate.decide(triage) now works
```

Adding a custom action type:

```python
from gate import GateAction

class NotifySlackAction:
    def apply(self, triage, decision, params):
        ...

gate.register_action("notify_slack", NotifySlackAction())
```

## File Layout

```
src/gate/
  __init__.py              # public API: Gate, GateAction, DataSource, GateDecision
  contracts.py             # Protocol definitions
  config.py                # pydantic models for YAML schema + loader
  engine.py                # Gate class: YAML interpretation, action & source registries, overrides
  decision.py              # GateDecision, VoiceCallSpec
  actions/
    handoff.py
    inject_data.py
    voice_response.py

examples/shopco/
  main.py                  # registers sources, wires FastAPI
  sources.py               # OrderSource, PolicySource, ContactsSource (move logic from src/repository.py)
  config/
    shopco.yaml            # declarative equivalent of current gate.py behaviour
  tests/
    test_shopco_flow.py    # acceptance tests against the full ShopCo config
```

Tests for the engine itself live in `tests/` at the repo root and use **mock sources and mock actions** — they verify YAML interpretation without any ShopCo data.

## Migration Plan (high level)

Detailed implementation plan is produced separately via writing-plans. Shape:

1. Introduce `src/gate/` package alongside existing `src/gate.py`. New code, no deletion yet.
2. Move data-access logic from `src/repository.py` into `examples/shopco/sources.py` wrapped as `DataSource` implementations.
3. Express current `gate.py` behaviour as `examples/shopco/config/shopco.yaml`, with personas registered from the existing `prompts/voice/*.md` files.
4. Port `test_gate.py` — engine-level assertions become `tests/test_engine.py` (mock sources); ShopCo-specific assertions become `examples/shopco/tests/test_shopco_flow.py`.
5. Update `src/orchestrator.py` and `src/api.py` to import from the new package and construct the `Gate` via `examples/shopco/main.py` wiring.
6. Delete `src/gate.py` and `src/repository.py`. Remove `VoicePersona` `Literal` from `src/models.py`.
7. Update `README.md` to document the framework vs. the ShopCo example.

Each step is independently testable; the existing scenario eval (`scripts/run_eval.py`) acts as the end-to-end verification that the ShopCo example still behaves identically after the refactor.

## Deferred / Open

- **Async sources.** Data sources are synchronous for now. Making them async requires propagating `await` through the gate and orchestrator. Deferred — no current source needs I/O beyond a JSON read.
- **Per-consumer packaging.** Publishing `gate` as a standalone PyPI package is out of scope for this refactor; we stop at clean internal boundaries within the repo.
- **Custom action hot-reload.** YAML reload at runtime. Deferred — consumer restarts the process to pick up config changes.
