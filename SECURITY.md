# Security Policy

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

This project uses **GitHub Security Advisories** for private vulnerability disclosure:

1. Go to the [Security tab](../../security/advisories/new) of this repository.
2. Click **"Report a vulnerability"**.
3. Describe the issue, steps to reproduce, and impact.

You should receive an acknowledgment within **7 days**. If the report is confirmed, we will coordinate a fix and a disclosure timeline with you before publishing any advisory.

## Scope

This is a **reference implementation** of the Triage-and-Voice pattern for safety-critical LLM products. Security-relevant areas include:

- Prompt injection / jailbreak bypasses of the triage + gate pipeline
- Data leakage through the voice layer (injected reference data exposed unintentionally)
- Dependency vulnerabilities in the listed runtime dependencies

Issues purely in example data (`data/`) or test scenarios (`tests/`) are generally **not** considered vulnerabilities unless they demonstrate a defect in the pattern itself.

## Supported Versions

Only the latest minor version on `main` receives security fixes while the project is pre-1.0.
