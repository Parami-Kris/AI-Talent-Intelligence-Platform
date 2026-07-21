"""Run the LLM-judgment-quality benchmark against the *live* Gemini API.

Unlike benchmarks/run_evaluation.py, this makes real model calls - it costs
quota and its exact scores aren't fully reproducible run to run, so it is
deliberately NOT wired into the default pytest suite or CI. Run it by hand
(e.g. before leaning on LLM-scoring quality as a portfolio claim) with:

    python -m benchmarks.run_llm_quality_eval
    python -m benchmarks.run_llm_quality_eval --report benchmarks/llm_quality_report.md

Requires GOOGLE_API_KEY to be set (see .env.example).
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from pipeline.matcher import education_match
from pipeline.shortlist_reranker import rerank_experience_relevance

from benchmarks.llm_quality_scenarios import EDUCATION_SCENARIOS, EXPERIENCE_SCENARIOS

load_dotenv()


def run_education_scenario(scenario):
    resume = {"education": scenario.candidate_education}
    jd = {"education_required": scenario.education_required}
    result = education_match(resume, jd)

    if isinstance(result, dict) and "error" in result:
        return result, [f"LLM response failed to parse: {result['error']}"]

    failures = []
    actual_status = result.get("status")
    if actual_status != scenario.expected_status:
        failures.append(f"Expected status '{scenario.expected_status}', got '{actual_status}'")
    return result, failures


def run_experience_scenario(scenario):
    rerank_results = rerank_experience_relevance([scenario.candidate_payload], scenario.jd)
    if not rerank_results:
        return None, ["LLM returned no rerank results"]

    result = rerank_results[0]
    if result.get("seniority_fit") == "not_evaluated":
        return result, [f"LLM response failed to parse: {result.get('reason')}"]

    failures = []
    score = result.get("experience_relevance_score")
    if score is None or not (scenario.expected_score_min <= score <= scenario.expected_score_max):
        failures.append(
            f"Expected experience_relevance_score in [{scenario.expected_score_min}, "
            f"{scenario.expected_score_max}], got {score}"
        )
    return result, failures


def format_report(education_results, experience_results):
    total = len(education_results) + len(experience_results)
    passed = sum(1 for _s, _r, failures in education_results if not failures) + sum(
        1 for _s, _r, failures in experience_results if not failures
    )

    lines = [
        "# LLM judgment-quality benchmark report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Result: {passed}/{total} scenarios agreed with the human label",
        "",
        "This checks the live Gemini model's actual judgment quality on "
        "education-match and experience-relevance scoring, not just the "
        "parsing/fallback code around it (see benchmarks/scenarios.py for that).",
        "",
        "## Education match",
        "",
    ]

    for scenario, result, failures in education_results:
        status = "AGREE" if not failures else "DISAGREE"
        lines.append(f"### [{status}] {scenario.name}")
        lines.append("")
        lines.append(scenario.description)
        lines.append(f"- Expected status: `{scenario.expected_status}`")
        lines.append(f"- LLM status: `{result.get('status') if isinstance(result, dict) else None}`")
        lines.append(f"- LLM reason: {result.get('reason') if isinstance(result, dict) else None}")
        for failure in failures:
            lines.append(f"- FAILURE: {failure}")
        lines.append("")

    lines.append("## Experience relevance")
    lines.append("")
    for scenario, result, failures in experience_results:
        status = "AGREE" if not failures else "DISAGREE"
        lines.append(f"### [{status}] {scenario.name}")
        lines.append("")
        lines.append(scenario.description)
        lines.append(f"- Expected score range: [{scenario.expected_score_min}, {scenario.expected_score_max}]")
        lines.append(f"- LLM score: {result.get('experience_relevance_score') if isinstance(result, dict) else None}")
        lines.append(f"- LLM reason: {result.get('reason') if isinstance(result, dict) else None}")
        for failure in failures:
            lines.append(f"- FAILURE: {failure}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run the LLM judgment-quality benchmark against live Gemini.")
    parser.add_argument("--report", default=None, help="Optional path to write a markdown report to.")
    args = parser.parse_args()

    if not os.getenv("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY is not set - this benchmark requires a live Gemini API key.", file=sys.stderr)
        sys.exit(1)

    education_results = [(s, *run_education_scenario(s)) for s in EDUCATION_SCENARIOS]
    experience_results = [(s, *run_experience_scenario(s)) for s in EXPERIENCE_SCENARIOS]

    report = format_report(education_results, experience_results)
    print(report)

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report)

    disagreements = [s.name for s, _r, failures in education_results if failures] + [
        s.name for s, _r, failures in experience_results if failures
    ]
    if disagreements:
        print(f"\n{len(disagreements)} scenario(s) disagreed with the label: {', '.join(disagreements)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
