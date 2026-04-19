# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- Initial reference implementation of the Triage-and-Voice pattern
- Domain models: `TriageResult`, `GateDecision`, `BotResponse`
- LLM-based triage module with retry on parse failure
- Deterministic backend gate with priority rules and data injection
- Voice module with persona prompts and Jinja2 data templating
- Orchestrator pipeline: triage → gate → voice with fallback
- FastAPI endpoints: `/chat/triage-voice`, `/chat/naive`, `/health`
- Naive single-prompt baseline bot for comparison
- Reference data repository (orders, policies, contacts)
- 12 test scenarios covering safety, legal, refund, jailbreak, multi-turn
- Side-by-side eval script comparing naive vs. triage-and-voice
- README with quickstart, pattern explanation, and eval instructions

[Unreleased]: ../../compare/v0.1.0...HEAD
[0.1.0]: ../../releases/tag/v0.1.0
