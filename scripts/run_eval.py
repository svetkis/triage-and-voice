"""Eval script — runs all scenarios through both bots and produces a comparison report."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Add project root to path so src imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models import ChatMessage  # noqa: E402
from src.naive.bot import process_message as naive_process  # noqa: E402
from src.orchestrator import process_message as triage_process  # noqa: E402

SCENARIOS_PATH = PROJECT_ROOT / "tests" / "scenarios.yaml"


def load_scenarios() -> list[dict]:
    """Load scenarios from YAML file."""
    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_history(scenario: dict) -> list[ChatMessage]:
    """Parse optional history field into ChatMessage objects."""
    history_raw = scenario.get("history", [])
    if not history_raw:
        return []
    return [ChatMessage(role=msg["role"], content=msg["content"]) for msg in history_raw]


def check_response(response_text: str, scenario: dict) -> tuple[bool, list[str]]:
    """Check must_contain and must_not_contain rules. Returns (passed, failures)."""
    text_lower = response_text.lower()
    failures: list[str] = []

    for term in scenario.get("must_contain", []):
        if term.lower() not in text_lower:
            failures.append(f"missing '{term}'")

    for term in scenario.get("must_not_contain", []):
        if term.lower() in text_lower:
            failures.append(f"contains forbidden '{term}'")

    return len(failures) == 0, failures


async def run_scenario(scenario: dict) -> dict:
    """Run a single scenario through both bots and return results."""
    sid = scenario["id"]
    user_message = scenario["user_message"]
    history = parse_history(scenario)

    print(f"  [{sid}] running naive...", end=" ", flush=True)
    naive_resp = await naive_process(user_message, history)
    naive_passed, naive_failures = check_response(naive_resp.text, scenario)
    print("✅" if naive_passed else "❌", end="  ", flush=True)

    print("running triage-and-voice...", end=" ", flush=True)
    tv_resp = await triage_process(user_message, history)
    tv_passed, tv_failures = check_response(tv_resp.text, scenario)
    print("✅" if tv_passed else "❌")

    return {
        "id": sid,
        "user_message": user_message,
        "expected_category": scenario.get("expected_category"),
        "expected_human_handoff": scenario.get("expected_human_handoff"),
        "naive": {
            "text": naive_resp.text,
            "human_handoff": naive_resp.human_handoff,
            "trace": naive_resp.trace,
            "passed": naive_passed,
            "failures": naive_failures,
        },
        "triage_and_voice": {
            "text": tv_resp.text,
            "human_handoff": tv_resp.human_handoff,
            "trace": tv_resp.trace,
            "passed": tv_passed,
            "failures": tv_failures,
        },
    }


def generate_report(results: list[dict]) -> str:
    """Generate markdown comparison report."""
    naive_passed = sum(1 for r in results if r["naive"]["passed"])
    tv_passed = sum(1 for r in results if r["triage_and_voice"]["passed"])
    total = len(results)

    lines: list[str] = [
        "# Eval Results: Naive vs Triage-and-Voice",
        "",
        f"**Naive:** {naive_passed}/{total} passed | **Triage-and-Voice:** {tv_passed}/{total} passed",
        "",
        "| Scenario | Naive | T&V | Difference |",
        "|----------|-------|-----|------------|",
    ]

    diff_details: list[dict] = []

    for r in results:
        n = "✅" if r["naive"]["passed"] else "❌"
        t = "✅" if r["triage_and_voice"]["passed"] else "❌"
        if r["naive"]["passed"] != r["triage_and_voice"]["passed"]:
            diff = "⚡"
            diff_details.append(r)
        else:
            diff = ""
        lines.append(f"| {r['id']} | {n} | {t} | {diff} |")

    lines.append("")

    if diff_details:
        lines.append("## Details")
        lines.append("")
        lines.append("_(only scenarios where results differ)_")
        lines.append("")

        for r in diff_details:
            lines.append(f"### {r['id']}")
            lines.append("")
            lines.append(f"**User message:** {r['user_message']}")
            lines.append("")

            lines.append("**Naive:**")
            lines.append(f"- Passed: {r['naive']['passed']}")
            if r["naive"]["failures"]:
                lines.append(f"- Failures: {', '.join(r['naive']['failures'])}")
            lines.append(f"- Response: {r['naive']['text'][:300]}...")
            lines.append("")

            lines.append("**Triage-and-Voice:**")
            lines.append(f"- Passed: {r['triage_and_voice']['passed']}")
            if r["triage_and_voice"]["failures"]:
                lines.append(f"- Failures: {', '.join(r['triage_and_voice']['failures'])}")
            lines.append(f"- Response: {r['triage_and_voice']['text'][:300]}...")
            lines.append("")

    return "\n".join(lines)


async def main():
    scenarios = load_scenarios()
    total = len(scenarios)
    print(f"Loaded {total} scenarios from {SCENARIOS_PATH.name}")
    print()

    results: list[dict] = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"[{i}/{total}] {scenario['id']}")
        result = await run_scenario(scenario)
        results.append(result)
        print()

    # Generate report
    report = generate_report(results)

    # Save to eval-runs/run-{timestamp}/
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = PROJECT_ROOT / "eval-runs" / f"run-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    results_json_path = run_dir / "results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved results JSON: {results_json_path}")

    report_path = run_dir / "report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Saved report: {report_path}")

    # Save to docs/eval_results.md
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    eval_results_path = docs_dir / "eval_results.md"
    with open(eval_results_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Saved docs report: {eval_results_path}")

    # Print summary
    print()
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
