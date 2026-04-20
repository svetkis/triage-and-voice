"""Eval script — runs all scenarios through both bots and produces a comparison report."""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

# Add project root to path so src imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from examples.shopco.main import build_pipeline  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.models import ChatMessage  # noqa: E402
from src.naive.bot import process_message as naive_process  # noqa: E402

SCENARIOS_PATH = PROJECT_ROOT / "tests" / "scenarios.yaml"

_PIPELINE = build_pipeline()


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
    tv_resp = await _PIPELINE.process_message(user_message, history)
    tv_passed, tv_failures = check_response(tv_resp.text, scenario)
    print("✅" if tv_passed else "❌")

    return {
        "id": sid,
        "user_message": user_message,
        "expected_category": scenario.get("expected_category"),
        "expected_human_handoff": scenario.get("expected_human_handoff"),
        "must_contain": scenario.get("must_contain", []),
        "must_not_contain": scenario.get("must_not_contain", []),
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


def _format_criteria(r: dict) -> str | None:
    """Render pass criteria from a scenario result as a one-line string."""
    parts: list[str] = []
    if r.get("must_contain"):
        parts.append("must contain: " + ", ".join(f"`{t}`" for t in r["must_contain"]))
    if r.get("must_not_contain"):
        parts.append("must not contain: " + ", ".join(f"`{t}`" for t in r["must_not_contain"]))
    return "; ".join(parts) if parts else None


def _format_response_block(label: str, side: dict) -> list[str]:
    """Render one bot's result: verdict, preview, and full text in <details>."""
    text = side["text"]
    preview = text[:300] + ("…" if len(text) > 300 else "")
    lines = [
        f"**{label}:**",
        f"- Passed: {side['passed']}",
    ]
    if side["failures"]:
        lines.append(f"- Failures: {', '.join(side['failures'])}")
    lines.append(f"- Response (preview): {preview}")
    lines.append("")
    lines.append("<details><summary>Full response</summary>")
    lines.append("")
    lines.append(text)
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return lines


def generate_report(results: list[dict], *, link_prefix: str, run_timestamp: str) -> str:
    """Generate markdown comparison report.

    link_prefix is prepended to repo-rooted paths (e.g. ``../../`` from
    ``eval-runs/run-*/report.md``) so links resolve from the report's location.
    """
    settings = get_settings()
    naive_passed = sum(1 for r in results if r["naive"]["passed"])
    tv_passed = sum(1 for r in results if r["triage_and_voice"]["passed"])
    total = len(results)

    lines: list[str] = [
        "# Eval Results: Naive vs Triage-and-Voice",
        "",
        f"**Naive:** {naive_passed}/{total} passed | **Triage-and-Voice:** {tv_passed}/{total} passed",
        "",
        "## Run metadata",
        "",
        f"- **Timestamp (UTC):** {run_timestamp}",
        f"- **Model:** `{settings.model}` · seed `{settings.llm_seed}` · timeout `{settings.llm_timeout_seconds}s` · max retries `{settings.llm_max_retries}`",
        f"- **Scenarios:** [`tests/scenarios.yaml`]({link_prefix}tests/scenarios.yaml)",
        f"- **Pattern entry points:** [`README.md`]({link_prefix}README.md) · [`prompts/`]({link_prefix}prompts/) · [`examples/shopco/prompts/`]({link_prefix}examples/shopco/prompts/) · [`examples/shopco/main.py`]({link_prefix}examples/shopco/main.py)",
        "- **Judge:** substring `must_contain` / `must_not_contain` rules from the scenario file (case-insensitive). Not an LLM judge.",
        "",
        "## Summary table",
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
    lines.append("_Legend: ✅ passed all rules · ❌ failed at least one rule · ⚡ the two bots disagree (usually T&V passes where Naive fails)._")
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

            criteria = _format_criteria(r)
            if criteria:
                lines.append(f"**Pass criteria:** {criteria}")
                lines.append("")

            lines.extend(_format_response_block("Naive", r["naive"]))
            lines.extend(_format_response_block("Triage-and-Voice", r["triage_and_voice"]))

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

    # Timestamps: one for filenames, one human-readable for the report body.
    now = datetime.now(UTC)
    ts = now.strftime("%Y%m%d-%H%M%S")
    run_timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Save to eval-runs/run-{timestamp}/
    run_dir = PROJECT_ROOT / "eval-runs" / f"run-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    results_json_path = run_dir / "results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved results JSON: {results_json_path}")

    # Report for eval-runs/run-*/report.md — links resolve via ../../ to repo root.
    run_report = generate_report(results, link_prefix="../../", run_timestamp=run_timestamp)
    report_path = run_dir / "report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(run_report)
    print(f"Saved report: {report_path}")

    # Report for docs/eval_results.md — links resolve via ../ to repo root.
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    docs_report = generate_report(results, link_prefix="../", run_timestamp=run_timestamp)
    eval_results_path = docs_dir / "eval_results.md"
    with open(eval_results_path, "w", encoding="utf-8") as f:
        f.write(docs_report)
    print(f"Saved docs report: {eval_results_path}")

    # Print summary
    print()
    print(run_report)


if __name__ == "__main__":
    asyncio.run(main())
