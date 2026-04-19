# Contributing

Thanks for your interest in contributing. This project is a **reference implementation** of the Triage-and-Voice pattern for safety-critical LLM products — scope is deliberately narrow.

## Before you start

- Open an **issue first** for any non-trivial change. A PR without a preceding issue is likely to be closed, because scope discussions happen on issues, not in review.
- Read [README.md](README.md) to understand what the pattern is and is not.

## Development setup

Requires **Python 3.11+**.

```bash
git clone <your-fork-url>
cd triage-and-voice
make install           # pip install -e ".[dev]"
cp .env.example .env   # add your OPENAI_API_KEY
make test              # pytest -v
make eval              # side-by-side eval: naive vs. triage-and-voice
make serve             # uvicorn on localhost:8000
```

## What kinds of contributions are welcome

- **Bug fixes** with a failing test that demonstrates the bug
- **New test scenarios** in `tests/` — especially adversarial ones (jailbreaks, prompt injection, multi-turn exploits) that the current pipeline fails on
- **Doc improvements** — clarity, typos, missing setup steps
- **New reference data** in `data/` that exposes gaps in the gate's priority rules

## Scope — what I may decline

This section will grow as patterns emerge in real PRs. The guiding principle:

> **The pattern's value comes from its constraints.** Changes that soften the separation between triage (classification), gate (deterministic routing), and voice (persona rendering) will be scrutinized heavily.

If you're unsure whether your idea fits, open an issue and ask before investing time.

## Pull request checklist

- [ ] Linked to an existing issue (or explained why one isn't needed)
- [ ] Tests pass: `make test`
- [ ] New code has test coverage
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Commit messages follow the existing style (see `git log`)

## Commit style

Conventional-ish, lowercase type prefix:

```
feat: add retry budget to triage classifier
fix: handle empty gate decision in orchestrator fallback
docs: clarify voice injection semantics in README
```

## Reporting security issues

Do **not** open a public issue for security vulnerabilities. See [SECURITY.md](SECURITY.md).
