"""Run the synthetic benchmark scenarios against the real ranking pipeline and
report pass/fail per scenario.

Usage:
    python -m benchmarks.run_evaluation [--report benchmarks/report.md]

Only exercises the deterministic parts of the pipeline (pipeline.batch_ranker,
pipeline.scoring_utils) - no Gemini calls, so this is free, fast, and safe to
run in CI. Exits non-zero if any scenario fails, so it can gate a build.
"""

import argparse
import sys
from datetime import datetime, timezone

from pipeline.batch_ranker import rank_candidates
from pipeline.shortlist_reranker import merge_rerank_results

from benchmarks.scenarios import SCENARIOS


def run_scenario(scenario):
    ranked = rank_candidates(scenario.candidates, scenario.jd)
    failures = []
    for check in scenario.checks:
        failures.extend(check(ranked))
    return ranked, failures


def run_all(scenarios):
    results = []
    for scenario in scenarios:
        try:
            _ranked, failures = run_scenario(scenario)
        except Exception as exc:  # noqa: BLE001 - want to report the failure, not crash the whole run
            failures = [f"Scenario raised an exception: {exc!r}"]
        results.append((scenario, failures))
    return results


def run_first_pass_vs_reranked_comparison():
    """Demonstrates why the shortlist reranking stage exists: a candidate can win
    on first-pass deterministic score alone but turn out to have weak domain
    relevance once an LLM actually reads the work history, and vice versa. Fully
    deterministic here (rerank_results are supplied directly) since the goal is to
    verify merge_rerank_results' blending/reordering behavior, not re-test the LLM
    prompt itself.
    """
    first_pass = [
        {
            "candidate_name": "High Score Weak Relevance",
            "overall_score": 90,
            "is_eligible": True,
            "rank": 1,
            "job_stability": {"flag": "stable", "average_tenure_years": 4, "short_stints_count": 0},
        },
        {
            "candidate_name": "Lower Score Strong Relevance",
            "overall_score": 70,
            "is_eligible": True,
            "rank": 2,
            "job_stability": {"flag": "stable", "average_tenure_years": 3, "short_stints_count": 0},
        },
    ]
    rerank_results = [
        {
            "candidate_name": "High Score Weak Relevance",
            "experience_relevance_score": 20,
            "seniority_fit": "weak",
            "domain_fit": "weak",
        },
        {
            "candidate_name": "Lower Score Strong Relevance",
            "experience_relevance_score": 95,
            "seniority_fit": "strong",
            "domain_fit": "strong",
        },
    ]

    final_results = merge_rerank_results(first_pass, rerank_results)

    first_pass_order = [c["candidate_name"] for c in sorted(first_pass, key=lambda c: c["overall_score"], reverse=True)]
    reranked_order = [c["candidate_name"] for c in final_results]

    failures = []
    if first_pass_order[0] != "High Score Weak Relevance":
        failures.append("Expected first-pass order to rank 'High Score Weak Relevance' first (by overall_score alone)")
    if reranked_order[0] != "Lower Score Strong Relevance":
        failures.append(
            "Expected the reranked order to promote 'Lower Score Strong Relevance' to first once LLM "
            "experience relevance is blended in (60% first-pass / 40% relevance)"
        )

    return first_pass_order, reranked_order, failures


def format_report(results, comparison):
    first_pass_order, reranked_order, comparison_failures = comparison
    total = len(results) + 1
    passed = sum(1 for _scenario, failures in results if not failures) + (0 if comparison_failures else 1)
    lines = [
        "# Ranking pipeline benchmark report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Result: {passed}/{total} scenarios passed",
        "",
    ]
    for scenario, failures in results:
        status = "PASS" if not failures else "FAIL"
        lines.append(f"## [{status}] {scenario.name}")
        lines.append("")
        lines.append(scenario.description)
        lines.append("")
        if failures:
            for failure in failures:
                lines.append(f"- {failure}")
            lines.append("")

    status = "PASS" if not comparison_failures else "FAIL"
    lines.append(f"## [{status}] first_pass_vs_reranked_comparison")
    lines.append("")
    lines.append(
        "Shows why the LLM reranking stage exists: first-pass order is deterministic-score-only, "
        "reranked order blends in LLM-judged experience relevance (60% first-pass / 40% relevance)."
    )
    lines.append("")
    lines.append(f"- First-pass order: {' > '.join(first_pass_order)}")
    lines.append(f"- Reranked order: {' > '.join(reranked_order)}")
    lines.append("")
    if comparison_failures:
        for failure in comparison_failures:
            lines.append(f"- {failure}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run synthetic ranking pipeline benchmark scenarios.")
    parser.add_argument("--report", default=None, help="Optional path to write a markdown report to.")
    args = parser.parse_args()

    results = run_all(SCENARIOS)
    comparison = run_first_pass_vs_reranked_comparison()
    report = format_report(results, comparison)
    print(report)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)

    failed = [scenario.name for scenario, failures in results if failures]
    if comparison[2]:
        failed.append("first_pass_vs_reranked_comparison")
    if failed:
        print(f"\n{len(failed)} scenario(s) failed: {', '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
