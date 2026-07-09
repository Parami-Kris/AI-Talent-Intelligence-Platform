from typing import Any

from batch_ranker import build_summary, rank_candidates


def rank_candidates_for_jd(
    jd: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    ranked = rank_candidates(candidates, jd)

    return {
        "job_title": jd.get("job_title"),
        "ranking_rule": "Eligible candidates first, then overall_score, then skill_score.",
        "summary": build_summary(ranked),
        "results": ranked,
    }
