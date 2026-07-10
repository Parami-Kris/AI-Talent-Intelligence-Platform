from typing import Any

from backend.app.ranking_repository import (
    insert_candidate_ranking,
    insert_score_evidence,
    insert_screening_run,
    upsert_candidate,
)
from pipeline.save_rankings_to_mysql import collect_evidence


def save_rankings_payload(
    rankings: dict[str, Any],
    run_name: str,
    source_file: str = "api_payload",
) -> dict[str, Any]:
    run_id = insert_screening_run(
        run_name=run_name,
        job_title=rankings.get("job_title"),
        ranking_rule=rankings.get("ranking_rule"),
        source_file=source_file,
    )

    saved_rankings = 0
    for result in rankings.get("results", []):
        candidate_id = upsert_candidate(
            name=result.get("candidate_name", "Unknown Candidate"),
            email=result.get("email"),
        )
        ranking_id = insert_candidate_ranking(run_id, candidate_id, result)

        for score_type, evidence_items in collect_evidence(result).items():
            insert_score_evidence(ranking_id, score_type, evidence_items)

        saved_rankings += 1

    return {
        "run_id": run_id,
        "saved_rankings": saved_rankings,
    }
